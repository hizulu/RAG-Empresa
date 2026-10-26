#Librerias
import os
import ssl
import time
import streamlit as st
from indexing import ingest_documents, get_folder_signature
from ai_logic import load_rag_assets, ask_assistant
from db_handler import save_user_on_db, verify_credentials, clean_text, update_question_count, verify_domain_credentials

colorBlue = "#008CA9"

current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.abspath(os.path.join(current_dir, "..", "data"))
DOCS_PATH = r"C:\TvitecGPT\Documentacion"
DB_PATH = os.path.join(DATA_PATH ,"db_vectorial")
REGISTRO_PATH = os.path.join(DATA_PATH, "registro.txt")

#Seguridad para evitar errores de certificados SSL
os.environ['CURL_CA_BUNDLE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context

st.set_page_config(page_title="Tvitec GPT", page_icon="🌐", layout="wide")

def main():
    #Configuración del título
    st.markdown(f"<h1 style='color: {colorBlue};'>Tvitec GPT</h1>", unsafe_allow_html=True)

    sign_out()
    #Verificación automática de la base de datos y actualización si es necesario
    check_database()

    retriever, llm = None, None

    if st.session_state.get("logged_in"):
        with st.spinner("Preparando el entorno para sus departamentos..."):
            retrievers = load_rag_assets(st.session_state.user_dept)

    st.markdown("<p style='font-size: 18px; font-weight: bold; margin-bottom: 5px;'>Fuente de consulta:</p>", unsafe_allow_html=True)
    fuente_seleccionada = st.radio(
    "Fuente de consulta:",
    ["Manuales y Documentación", "Bases de Datos SQL"],
    index=0,
    horizontal=True,
    label_visibility="collapsed"
    )

    #Boton Preguntar
    st.markdown("""<style> [data-testid="stForm"] {border: none; padding: 0;}div.stButton > button[kind="primary"] {background-color: #ED6A26; color: white; } </style>""", unsafe_allow_html=True)
    with st.form(key="chat_form"):
        st.markdown("<p style='font-size: 18px; font-weight: bold; margin-bottom: 5px;'>Realice su pregunta:</p>", unsafe_allow_html=True)
        user_query = st.text_input("Realice su pregunta:", label_visibility="collapsed")
        submit_button = st.form_submit_button("Preguntar", type="primary")

    if submit_button and user_query:
        with st.spinner("Pensando..."):
            try:
                    response = ask_assistant(user_query, st.session_state.user_dept, fuente_seleccionada)
                    st.session_state.countPreguntas += 1
                    update_question_count(st.session_state.user_info['Usuario'], st.session_state.countPreguntas)                    
                    st.subheader("Respuesta:")
                    st.markdown(response)            
                    
            except Exception as e:
                error_message = str(e).lower()

                if "overloaded" in error_message:
                    st.error("El servidor de Anthropic está saturado en este momento. Por favor, inténtalo de nuevo en unos segundos.")
                elif "max_tokens" in error_message or "context_length" in error_message:
                    st.error("La consulta es demasiado extensa. El conjunto de documentos encontrados supera el límite permitido. Prueba a ser más específico en tu pregunta.")
                elif "rate_limit" in error_message:
                    st.error("Se ha alcanzado el límite de peticiones por minuto. Espera un momento antes de volver a preguntar.")
                else:
                    st.error(f"Ha ocurrido un error inesperado: {str(e)}")
                    print(f"Error detallado: {e}")
                    
#Función de Verificación Automática
def check_database():
    if st.session_state.get("indexing_done", False):
        return

    firma_actual = get_folder_signature(DOCS_PATH)
    
    firma_indexada = ""
    if os.path.exists(REGISTRO_PATH):
        with open(REGISTRO_PATH, "r") as f:
            firma_indexada = f.read().strip()

    db_existe = os.path.exists(DB_PATH) and any(os.scandir(DB_PATH))

    if not db_existe or firma_actual != firma_indexada:
        with st.status("Detectados cambios en documentos. Sincronizando...", expanded=True) as status:
            ingest_documents()
            
            if os.path.exists(REGISTRO_PATH):
                with open(REGISTRO_PATH, "r") as f:
                    nueva_firma = f.read().strip()
                
                if nueva_firma == firma_actual:
                    st.session_state.indexing_done = True
                    st.cache_resource.clear()
                    status.update(label="Base de datos actualizada", state="complete", expanded=False)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Error: La firma no se actualizó correctamente.")
            else:
                st.error("Error al generar el archivo de registro.")

#Función de Inicio de Sesión
def sign_in():
    st.markdown("""<style> [data-testid="stForm"] {border: none; padding: 0;}div.stButton > button[kind="primary"] {background-color: #ED6A26; color: white; } </style>""", unsafe_allow_html=True)
    with st.form(key="signIn_form"):
        st.markdown(f"<h1 style='color: {colorBlue}; text-align: center'>Inicio de Sesión</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<p style='font-size: 18px; font-weight: bold; margin-bottom: 5px;'>Usuario</p>", unsafe_allow_html=True)
            col_izq, col_der = st.columns([0.08, 0.92], vertical_alignment="center")
            with col_izq:
                st.markdown("**TVITEC\\\\**")
            with col_der:
                user = st.text_input("Usuario *", label_visibility="collapsed", key="user_input")
            
            st.markdown("<p style='font-size: 18px; font-weight: bold; margin-bottom: 5px;'>Contraseña</p>", unsafe_allow_html=True)
            password = st.text_input("Contraseña", type="password", label_visibility="collapsed", key="pass_input")

            submit_button = st.form_submit_button("Ingresar", type="primary", use_container_width=True)
            
            if submit_button:
                if not user or not password:
                    st.warning("Por favor, introduzca su usuario y contraseña.")
                else:
                    resultado = verify_domain_credentials(user, password)
                    
                    if resultado["success"]:
                        nombre = resultado["nombre"]
                        apellidos = resultado["apellidos"]
                        depts_lista = resultado["departamento"] 

                        if isinstance(depts_lista, list):
                            dept_clean = ", ".join([clean_text(d).upper().strip() for d in depts_lista])
                        else:
                            dept_clean = clean_text(depts_lista).upper().strip()
                        
                        save_user_on_db(nombre, apellidos, user, dept_clean, 0)
                        
                        user_data = verify_credentials(user)
                        
                        st.session_state.logged_in = True
                        st.session_state.user_info = user_data
                        st.session_state.user_dept = user_data['Departamentos']
                        st.session_state.user_name = f"{user_data['Nombre']} {user_data['Apellidos']}"
                        st.session_state.countPreguntas = int(user_data.get('Preguntas hechas', 0))
              
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña de dominio incorrectos.")
#Cierre de sesion
def sign_out():
    with st.sidebar:
        st.markdown(f"### Usuario: {st.session_state.get('user_name', 'Invitado')}")
        st.markdown(f"**Departamento:** {st.session_state.get('user_dept', 'General').replace("_", " ")}")
        st.divider()
        
        if st.button("Cerrar Sesión", type="secondary", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_dept = None
            st.session_state.user_name = None
            
            st.rerun()                    

#Punto de entrada
#Si el usuario no ha iniciado sesión, se muestra la pantalla de inicio de sesión. De lo contrario, se muestra la aplicación principal.
if __name__ == "__main__":
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if 'current_screen' not in st.session_state:
        st.session_state.current_screen = "login"

    if not st.session_state.logged_in:
        if st.session_state.current_screen == "login":
            sign_in()
    else:
        main()