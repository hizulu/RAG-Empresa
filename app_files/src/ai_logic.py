import os
import json
import streamlit as st
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.agents.format_scratchpad import format_to_tool_messages
from langchain_classic.agents.output_parsers import ToolsAgentOutputParser
from langchain_classic.agents.agent import AgentExecutor
from langchain_core.tools import Tool
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_classic.retrievers import ParentDocumentRetriever
from langchain_classic.storage import LocalFileStore, EncoderBackedStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from sql_handler import get_single_db_connection

current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.abspath(os.path.join(current_dir, "..", "data"))
DB_PATH = os.path.join(DATA_PATH ,"db_vectorial")
PARENT_STORE_PATH = os.path.join(DATA_PATH ,"db_parents")

load_dotenv()

@st.cache_resource
def get_llm(model_name="claude-sonnet-4-6"):
    return ChatAnthropic(model=model_name, temperature=0)

@st.cache_resource
def load_rag_assets(user_depts_str):
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    depts_to_load = [d.strip() for d in user_depts_str.split(", ")]
    if "General" not in depts_to_load:
        depts_to_load.append("General")

    retrievers = []
    for depto in depts_to_load:
        depto_db_path = os.path.join(DB_PATH, depto)
        depto_parent_path = os.path.join(PARENT_STORE_PATH, depto)

        if os.path.exists(depto_db_path) and os.listdir(depto_db_path):
            vector_db = Chroma(
                collection_name=f"split_{depto}", 
                persist_directory=depto_db_path, 
                embedding_function=embeddings
            )
            fs = LocalFileStore(depto_parent_path)
            
            store = EncoderBackedStore(
                store=fs,
                key_encoder=lambda x: x,
                value_serializer=lambda d: json.dumps({"page_content": d.page_content, "metadata": d.metadata}).encode("utf-8"),
                value_deserializer=lambda b: Document(**json.loads(b.decode("utf-8")))
            )

            r = ParentDocumentRetriever(
                vectorstore=vector_db,
                docstore=store,
                child_splitter=RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=500),
                parent_splitter=RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=1000, add_start_index=True),
            )
            retrievers.append(r)
            
    return retrievers

@st.cache_resource
def get_sql_toolkit(db_id):
    llm = get_llm()
    db_conn = get_single_db_connection(db_id)
    tools = SQLDatabaseToolkit(db=db_conn, llm=llm).get_tools()
    for t in tools:
        if not t.name.startswith(f"{db_id}_"):
            t.name = f"{db_id}_{t.name}"
    return tools

def load_full_agent(user_query, user_depts_str, fuente_seleccionada):
    all_tools = []
    
    if fuente_seleccionada == "Manuales y Documentación":
        llm = get_llm("claude-sonnet-4-6")
        retrievers = load_rag_assets(user_depts_str)
        
        def search_docs(query: str):
            results = []
            for r in retrievers:
                docs = r.vectorstore.similarity_search(query, k=5)
                results.extend([d.page_content for d in docs])
            return "\n\n".join(results) if results else "No se encontró información."

        all_tools.append(Tool(
            name="Buscador_Manuales",
            func=search_docs,
            description="Acceso a manuales de TVITEC. Úsalo para teclas, procesos y 'cómo se hace'."
        ))
        system_prompt = "Eres experto en manuales de TVITEC. Si preguntan por procesos, técnicas u otras acciones similares, usa el Buscador_Manuales. Responde ampliamente, paso por paso."

    else:
        llm = get_llm("claude-sonnet-4-6")
        #TODO: cambiar bases de datos
        prioridades = {
            "FVMASTER": "Orders, OrderDetail, Invoice, InvoiceDetail, Customers, OrderDetailAttributes, OrderUserDefValues, Invoices, InvMaster, InventoryBinsDetail, InventoryBinsDetailLots, InventoryTransDetail, ReceiptDetailLots, MasterPartList, TrackingHistory, WorkCells, WorkCellStations, ContainerMfgUnits, ProdDetails, ScheduleDetail, RouteTrucks, RouteStops, HarpRacks, Receipts, ReceiptDetail",
            "FVCUSTOM": "TVI_Produccion_CortePorHoja, TVI_Produccion_Manu, TVI_Produccion_Manu_Historico, TVI_Produccion_Serig, TVI_Produccion_Serig_Hist, TVI_Produccion_Horno, TVI_Produccion_Horno_Hist, TVI_ProduccionLami, TVI_ProduccionLami_Hist, TVI_Produccion_Doble, TVI_Produccion_Doble_Hist, TVI_PARTES_CABECERA, TVI_LoginOperarios, TVI_Usuarios, TVI_SECCIONES, TVI_ESTACIONES, TVI_ESTACIONES_SECCIONES, TVI_ObsPiman, TVI_ObsPiman2, TVI_ENVIO_CALIDAD, TVI_OptimizacionesAsignadas, TVI_OptiLanzadas, TVI_HistoricoOptisCabecera, TVI_CapacidadesMesasCorte, TVI_AjustesStock, TVI_Proveedores, TVI_VISUALCAP_COMENTARIOS, TVI_InfoContainersLAMI_Log",
            "FVOptiglass": "PatternDetail, Releases, Remakes, Machines, MachineParameters, GeneralSetup, Locations, StockSizes, StoreSizes, RackDetail, Racks, Part, uvw_storeSizes",
        }

        for db_id in ["FVCUSTOM", "FVMASTER", "FVOptiglass"]:
            tools = get_sql_toolkit(db_id)
            all_tools.extend(tools)
        
        system_prompt = f"""Eres experto en bases de datos SQL de TVITEC. 
        REGLAS DE ORO:
        1. Para responder, busca SIEMPRE primero en estas tablas prioritarias:
           - FVMASTER: {prioridades['FVMASTER']}
           - FVCUSTOM: {prioridades['FVCUSTOM']}
           - FVOptiglass: {prioridades['FVOptiglass']}
        
        2. CUANDO ENCUENTRES LA INFORMACIÓN QUE RESPONDE A LA PREGUNTA, DETENTE INMEDIATAMENTE. No sigas buscando en otras tablas o bases de datos por curiosidad. Genera tu respuesta final con los datos que ya tienes.
        
        Si y SOLO SI la información no está en esas tablas, usa la herramienta 'list_tables' para descubrir otras opciones."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"{system_prompt} Responde en español. Si no sabes algo, no lo inventes."),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = (
        {
            "input": lambda x: x["input"],
            "agent_scratchpad": lambda x: format_to_tool_messages(x["intermediate_steps"]),
            "chat_history": lambda x: x.get("chat_history", []),
        }
        | prompt
        | llm.bind_tools(all_tools)
        | ToolsAgentOutputParser()
    )
    
    return AgentExecutor(agent=agent, tools=all_tools, verbose=True, max_iterations=15)

def ask_assistant(user_query, user_depts_str, fuente_seleccionada):
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    memoria_limitada = st.session_state.chat_history[-6:]

    agent_executor = load_full_agent(user_query, user_depts_str, fuente_seleccionada)
    
    raw_result = agent_executor.invoke({
        "input": user_query,
        "chat_history": memoria_limitada 
    })
    
    respuesta = raw_result.get("output", str(raw_result))
    if isinstance(respuesta, list):
        respuesta = respuesta[0].get("text", "")
        
    st.session_state.chat_history.append(("human", user_query))
    st.session_state.chat_history.append(("ai", respuesta))
    
    return respuesta