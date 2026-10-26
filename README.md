# 🌐 Asistente Corporativo RAG & SQL (TvitecGPT)

TvitecGPT es una solución integral de inteligencia artificial diseñada para centralizar el conocimiento de **Tvitec**. Combina la potencia de **RAG (Generación Aumentada por Recuperación)** para manuales técnicos con un **Agente SQL** capaz de consultar datos de producción en tiempo real.

> Enlace al coste del Anthropic API: [Coste Anthropic API](https://platform.claude.com/workspaces/default/cost)

---
| Inicio de Sesión | Pantalla de consulta |
| :---: | :---: |
| <img width="600" alt="image" src="https://github.com/user-attachments/assets/fc1eee3c-e4db-4183-9ffc-99c459b463f0" /> | <img width="600" alt="image" src="https://github.com/user-attachments/assets/cc929533-4491-4b88-a1f5-ff1401c11ad1" /> |

|  Búsqueda en manuales | Búsqueda en bases de datos SQL |
| :---: | :---: |
| <img width="600" alt="image" src="https://github.com/user-attachments/assets/2b855722-46c5-4755-958e-a32f410802a3" /> | <img width="600" alt="Lucía garcía lópez (1)" src="https://github.com/user-attachments/assets/bd657d03-edbe-4623-b530-9d7688ad3461" /> |

---
## Características Principales

* **Agente SQL Multibase:** Consulta inteligente sobre `FVMASTER`, `FVCUSTOM` y `FVOptiglass`. Rastreo de lotes, pedidos, stock y estados de fabricación.
* **RAG de Documentación:** Acceso a manuales en PDF, Word, Excel y TXT con indexación automática mediante hashes MD5 para detectar cambios.
* **Seguridad y Acceso:** Validación mediante **Directorio Activo (AD)**.
    * Filtrado por departamentos: solo ves lo que te corresponde.
* **Control de Uso:** Registro de actividad y estadísticas de consultas por usuario en bases de datos locales.

---

## Tecnologías Utilizadas

| Componente | Tecnología |
| :--- | :--- |
| **Frontend** | [Streamlit](https://streamlit.io/) |
| **Cerebro (LLM)** | [Anthropic Claude 4.6 Sonnet](https://www.anthropic.com/claude) |
| **Orquestación** | [LangChain](https://python.langchain.com/) |
| **Base de Datos Vectorial** | [ChromaDB](https://www.trychroma.com/) |
| **Embeddings** | HuggingFace (Local: `all-MiniLM-L6-v2`) |
| **Conectividad SQL** | SQLAlchemy + pyodbc (ODBC Driver 18) |

---
# PARA DESCARGAR
Se debe clonar el proyecto y moverse hasta la carpeta src (`RAG\app_files\src`).
Una vez dentro deben lanzarse los siguiente comandos en la terminal de tipo Git Bash:
> py -m venv .venv
> 
> source .venv/Scripts/activate
> 
> py -m pip install -r requirements.txt

Y cambiar las rutas de los diferentes archivos de la siguiente manera:

### ⚠️ AVISO IMPORTANTE: Configuración de Rutas
El proyecto está preconfigurado con las rutas locales del servidor de **TVITEC** (ej. `C:\TvitecGPT\Documentacion`).

Si planeas ejecutar este asistente en un entorno diferente, **debes actualizar obligatoriamente**:
1. `DOCS_PATH` en `indexing.py` y  `chat.py`.
2. Las IPs de los servidores en `sql_handler.py`.

---

## 📂 Estructura del Proyecto

```text
📂 RAG/
├── 📂 app_files/
│   ├── 📂 src/
│   │   ├── chat.py             # Interfaz de usuario (Streamlit)
│   │   ├── ai_logic.py         # Cerebro del agente y lógica RAG
│   │   ├── sql_handler.py      # Conexiones y esquemas de SQL Server
│   │   ├── indexing.py         # Sincronizador de documentos
│   │   └── db_handler.py       # Lógica de usuarios y Directorio Activo
│   └── 📂 data/
│       ├── usuarios_db.csv     # Registro de consultas y perfiles
│       ├── file_register.json  # Control de versiones de archivos
│       ├── 📂 db_parents/      # Almacén de documentos originales
│       └── 📂 db_vectorial/    # Almacén de vectores (Chroma)
└── ⚙ RAG_Asistente.bat         # Lanzador de la aplicación
