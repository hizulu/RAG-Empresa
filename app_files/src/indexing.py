#Librerias
import os
import json
import hashlib
from langchain_chroma import Chroma 
from langchain_community.document_loaders import PyPDFLoader, UnstructuredExcelLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_classic.retrievers import ParentDocumentRetriever
from langchain_classic.storage import LocalFileStore, EncoderBackedStore
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

#Rutas
DOCS_PATH = r"C:\TvitecGPT\Documentacion"
current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.abspath(os.path.join(current_dir, "..", "data"))
if not os.path.exists(DATA_PATH):
    os.makedirs(DATA_PATH, exist_ok=True)
DB_PATH = os.path.join(DATA_PATH ,"db_vectorial")
PARENT_STORE_PATH = os.path.join(DATA_PATH ,"db_parents")
JSON_REGISTER = os.path.join(DATA_PATH, "file_register.json")
LOCK_FILE = os.path.join(DATA_PATH, "indexing.lock")

def ingest_documents():
    if os.path.exists(LOCK_FILE):
        print("Ya hay una indexación en curso por otro usuario...")
        return
        
    try:
        open(LOCK_FILE, 'w').close()
        
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2", cache_folder="C:/temp/models_cache")
        
        register = {}
        if os.path.exists(JSON_REGISTER):
            with open(JSON_REGISTER, "r") as f:
                register = json.load(f)

        current_files_on_disk = {}
        files_by_depto = {}
        EXCLUDED_FOLDERS = ["RAG", ".venv", "__pycache__", "db_vectorial", "db_parents", "app_files", "Instalacion"]

        for current_root, dirs, files in os.walk(DOCS_PATH):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_FOLDERS]
            folder_name = os.path.basename(current_root)
            
            if folder_name in EXCLUDED_FOLDERS:
                continue

            tag_depto = folder_name.replace("Dep_", "").upper().strip() if folder_name.startswith("Dep_") else "GENERAL"            
            
            if tag_depto not in files_by_depto:
                files_by_depto[tag_depto] = []

            for file in files:
                if file.startswith("~$") or file.endswith((".py", ".vbs", ".bat", ".env", ".csv", ".json")):
                    continue
                    
                path = os.path.join(current_root, file)
                file_hash = get_file_hash(path)
                current_files_on_disk[file] = {"path": path, "depto": tag_depto, "hash": file_hash}
                files_by_depto[tag_depto].append(file)

        to_delete_files = set(register.keys()) - set(current_files_on_disk.keys())
        for f_name in to_delete_files:
            info_reg = register[f_name]
            depto_reg = info_reg["depto"] if isinstance(info_reg, dict) else "General"
            db_path_to_clean = os.path.join(DB_PATH, depto_reg)
            
            if os.path.exists(db_path_to_clean):
                vdb_temp = Chroma(collection_name=f"split_{depto_reg}", persist_directory=db_path_to_clean, embedding_function=embeddings)
                vdb_temp.delete(where={"source": f_name})
            
            del register[f_name]

        for depto, lista_archivos in files_by_depto.items():
            depto_db_path = os.path.join(DB_PATH, depto)
            depto_parent_path = os.path.join(PARENT_STORE_PATH, depto)
            
            if not os.path.exists(depto_db_path): os.makedirs(depto_db_path)
            if not os.path.exists(depto_parent_path): os.makedirs(depto_parent_path)

            vector_db = Chroma(collection_name=f"split_{depto}", embedding_function=embeddings, persist_directory=depto_db_path)
            fs = LocalFileStore(depto_parent_path)
            
            store = EncoderBackedStore(
                store=fs,
                key_encoder=lambda x: x,
                value_serializer=lambda d: json.dumps({"page_content": d.page_content, "metadata": d.metadata}).encode("utf-8"),
                value_deserializer=lambda b: Document(**json.loads(b.decode("utf-8")))
            )

            retriever = ParentDocumentRetriever(
                vectorstore=vector_db,
                docstore=store,
                child_splitter=RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=500),
                parent_splitter=RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=1000, add_start_index=True),
            )

            for file_name in lista_archivos:
                info = current_files_on_disk[file_name]
                reg_entry = register.get(file_name, {})
                old_hash = reg_entry.get("hash") if isinstance(reg_entry, dict) else reg_entry

                if file_name not in register or old_hash != info["hash"]:
                    if file_name in register:
                        vector_db.delete(where={"source": file_name})

                    docs = charge_file(info["path"], info["depto"])
                    if docs:
                        batch_size = 1
                        for i in range(0, len(docs), batch_size):
                            batch = docs[i : i + batch_size]
                            retriever.add_documents(batch)
                            
                    register[file_name] = {"hash": info["hash"], "depto": depto}

        with open(JSON_REGISTER, "w") as f:
            json.dump(register, f)
        
        firma_actual = get_folder_signature(DOCS_PATH)
        with open(os.path.join(DATA_PATH, "registro.txt"), "w") as f:
            f.write(firma_actual)

        print("--- Proceso de indexación estanca finalizado ---")
        
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

def get_folder_signature(path):
    signature_parts = []
    excluded_dirs = {"RAG", "app_files", "db_vectorial", "db_parents", ".venv", "__pycache__"}
    
    for root, dirs, files in os.walk(path):
        dirs[:] = sorted([d for d in dirs if d not in excluded_dirs])
        
        for file in sorted(files):
            if file.startswith("~$") or file.startswith(".") or file.lower() in ["desktop.ini", ".ds_store"]:
                continue
                
            file_path = os.path.join(root, file)
            try:
                stats = os.stat(file_path)
                mtime = int(stats.st_mtime) 
                size = stats.st_size
                rel_path = os.path.relpath(file_path, path)
                signature_parts.append(f"{rel_path}_{mtime}_{size}")
            except (OSError, PermissionError):
                continue
    
    if not signature_parts:
        return "empty"
        
    signature_string = "|".join(sorted(signature_parts))
    return hashlib.md5(signature_string.encode()).hexdigest()

def get_file_hash(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def charge_file(complete_path, tag_depto):
    complete_path = os.path.normpath(complete_path)
    file = os.path.basename(complete_path)

    #Ignorar archivos temporales
    if file.startswith("~$"):
        return []

    data = []
    try:
        if file.endswith(".pdf"):
            print(f"Cargando PDF: {file}")
            loader = PyPDFLoader(complete_path)
            data = loader.load()

        elif file.endswith(".docx"):
            print(f"Cargando Word: {file}")
            loader = Docx2txtLoader(complete_path)
            data = loader.load()

        elif file.endswith(".txt"):
            print(f"Cargando Texto: {file}")
            loader = TextLoader(complete_path, encoding="utf-8")
            data = loader.load()
            
        elif file.endswith((".xlsx", ".xls")):
            print(f"Cargando Excel: {file}")
            loader = UnstructuredExcelLoader(complete_path)
            data = loader.load()
        else:
            print("Documento con formato diferente")
            return[]
            
        #Añadir metadata y encabezado
        for d in data:
            d.metadata.update({"departamento": tag_depto, "source": file})
            d.page_content = f"[Archivo: {file} | Depto: {tag_depto}]\n\n" + d.page_content
            
        return data

    except Exception as e:
        print(f"Error procesando {file}: {str(e)}")
        return []