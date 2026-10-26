@echo off
cd /d "C:\TvitecGPT\RAG\app_files\src"
echo Activando entorno virtual...
call .venv\Scripts\activate
echo Lanzando Streamlit...
streamlit run chat.py --server.port 8501 --server.address 0.0.0.0
pause