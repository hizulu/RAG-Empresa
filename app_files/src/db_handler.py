import pandas as pd
import unicodedata
import hashlib
import ldap3

from ldap3 import Server, Connection, ALL, NTLM
try:
    hashlib.new('md4')
except ValueError:
    import os
    os.environ["OPENSSL_CONF"] = "" 

current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.abspath(os.path.join(current_dir, "..", "data"))
file_name = os.path.join(DATA_PATH, 'usuarios_db.csv')
if not os.path.exists(DATA_PATH):
    os.makedirs(DATA_PATH)

def verify_domain_credentials(user, password):
    LDAP_SERVER = '192.168.1.226' 
    
    user_ntlm = f"{user}@tvitec.local"
    
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        
        conn = Connection(server, user=user_ntlm, password=password, authentication="SIMPLE")
        
        if conn.bind():
            base_dn = "DC=tvitec,DC=local" 
            
            search_filter = f"(sAMAccountName={user})"
            conn.search(base_dn, search_filter, attributes=['givenName', 'sn', 'department', 'memberOf'])
            if conn.entries:
                entry = conn.entries[0]
                nombre = str(entry.givenName.value) if entry.givenName.value else "Usuario"
                apellidos = str(entry.sn.value) if entry.sn.value else "Tvitec"
                
                grupos_raw = entry.memberOf.value if entry.memberOf.value else []
                departamento = extract_departament(grupos_raw)

                return {
                    "success": True,
                    "nombre": str(entry.givenName.value) if entry.givenName.value else "Usuario",
                    "apellidos": str(entry.sn.value) if entry.sn.value else "Tvitec",
                    "departamento": departamento
                }
            
            return {"success": True, "nombre": "Usuario", "apellidos": "Tvitec", "departamento": "General"}
        
        else:
            print(f"Fallo en Bind: {conn.result}")
            return {"success": False}
            
    except Exception as e:
        print(f"Error LDAP: {e}")
        return {"success": False}  

#region Gestion Departamentos
def extract_departament(grupos_dn):
    if not grupos_dn:
        return ["General"]

    nombres_crudos = [g.split(',')[0].replace('CN=', '') for g in grupos_dn]
    
    mis_departamentos = []
    
    prefijos_validos = ("G_", "DEP_", "Dep_") 

    for nombre in nombres_crudos:
        nombre_up = nombre.upper()
        
        if nombre_up.startswith(prefijos_validos):
            
            palabras_tecnicas = [
                "O365", "MFA", "DOMAIN", "USUARIOS", "ACCESO", "VPN",
                "PRINT", "WINDOWS", "TODOS", "GS_", "SQL", "NIVELES", "FIRMAS", "CORREO",
                "WATCHGUARD", "WETRANSFER", "NAVEGACION", "FENEVISION", "FENETECH"]
            if any(tecnico in nombre_up for tecnico in palabras_tecnicas):
                continue
                
            dept_limpio = clean_depart_name(nombre)
            mis_departamentos.append(dept_limpio)

    return mis_departamentos if mis_departamentos else ["General"]

def clean_depart_name(nombre_raw):
    prefijos = ["G_", "GS_", "DPTO_", "DEP_", "UNIT_"]
    nombre = nombre_raw
    for prefijo in prefijos:
        if nombre.upper().startswith(prefijo):
            nombre = nombre[len(prefijo):]
    
    nombre = nombre.replace("_", " ").strip().capitalize()
    return nombre
#endregion

def verify_credentials(usuario_input):    
    if not os.path.isfile(file_name):
        return None
    
    df = pd.read_csv(file_name, encoding='utf-8-sig', sep=';')
    
    usuario_valido = df[df['Usuario'] == usuario_input]
    
    if not usuario_valido.empty:
        return usuario_valido.iloc[0].to_dict()
    
    return None

def save_user_on_db(nombre, apellidos, usuario, dept_string, countPreguntas):
    columnas = ["Nombre", "Apellidos", "Usuario", "Departamentos", "Preguntas hechas"]
    
    if os.path.exists(file_name):
        df = pd.read_csv(file_name, sep=';', encoding='utf-8-sig')
    else:
        df = pd.DataFrame(columns=columnas)

    if not df.empty and usuario in df['Usuario'].astype(str).values:
        idx = df.index[df['Usuario'].astype(str) == str(usuario)][0]
        count_actual = df.at[idx, "Preguntas hechas"]
        
        df.at[idx, "Nombre"] = nombre
        df.at[idx, "Apellidos"] = apellidos
        df.at[idx, "Departamentos"] = dept_string
        df.at[idx, "Preguntas hechas"] = count_actual
        
        print(f"Usuario {usuario} actualizado en CSV.")
    else:
        nueva_fila = pd.DataFrame([{
            "Nombre": nombre,
            "Apellidos": apellidos,
            "Usuario": usuario,
            "Departamentos": dept_string,
            "Preguntas hechas": countPreguntas
        }])
        df = pd.concat([df, nueva_fila], ignore_index=True)
        print(f"Usuario {usuario} creado en CSV.")

    df.to_csv(file_name, index=False, sep=';', encoding='utf-8-sig')
    return True

def clean_text(department):
    # Eliminar tildes y acentos
    department = unicodedata.normalize('NFD', department)
    department = department.encode('ascii', 'ignore').decode("utf-8")

    # Reemplazar espacios por guiones bajos
    return department.replace(" ", "_")

def update_question_count(usuario, nuevo_conteo):
    if os.path.exists(file_name):
        df = pd.read_csv(file_name, sep=';', encoding='utf-8-sig')
        if usuario in df['Usuario'].values:
            df.loc[df['Usuario'] == usuario, "Preguntas hechas"] = nuevo_conteo
            df.to_csv(file_name, index=False, sep=';', encoding='utf-8-sig')