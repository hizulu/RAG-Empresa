import os
import pydoc
import streamlit as st
from langchain_community.utilities import SQLDatabase
from urllib.parse import quote_plus
from sqlalchemy import create_engine

SERVER_IP = '192.168.4.170' 
USERNAME = 'lucia'
PASSWORD = '12Lucia21'

@st.cache_resource
def get_single_db_connection(db_name):
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={SERVER_IP},1433;"
        f"DATABASE={db_name};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD};"
        f"Encrypt=no;TrustServerCertificate=yes;"
    )
    print({db_name})
    uri = f"mssql+pyodbc:///?odbc_connect={quote_plus(conn_str)}"
    engine = create_engine(uri, pool_pre_ping=True, future=True)
    tablas_a_incluir = [] 
    
    if db_name == "FVMASTER":
        tablas_a_incluir = [
            "Orders", "OrderDetail", "Invoice", "InvoiceDetail", "Customers",
            "OrderDetailAttributes", "OrderUserDefValues",
            "Invoices", "InvMaster", "InventoryBinsDetail", 
            "InventoryBinsDetailLots", "InventoryTransDetail", "ReceiptDetailLots", 
            "MasterPartList", "TrackingHistory", "WorkCells", 
            "WorkCellStations", "ContainerMfgUnits", "ProdDetails", 
            "ScheduleDetail", "RouteTrucks", "RouteStops", "HarpRacks", "Receipts", "ReceiptDetail"            
        ]
        
    elif db_name == "FVCUSTOM":
        tablas_a_incluir = [
            "TVI_Produccion_CortePorHoja", "TVI_Produccion_Manu", "TVI_Produccion_Manu_Historico", 
            "TVI_Produccion_Serig", "TVI_Produccion_Serig_Hist", "TVI_Produccion_Horno", 
            "TVI_Produccion_Horno_Hist", "TVI_ProduccionLami", "TVI_ProduccionLami_Hist", 
            "TVI_Produccion_Doble", "TVI_Produccion_Doble_Hist", "TVI_PARTES_CABECERA", 
            "TVI_LoginOperarios", "TVI_Usuarios", "TVI_SECCIONES", "TVI_ESTACIONES", 
            "TVI_ESTACIONES_SECCIONES", "TVI_ObsPiman", "TVI_ObsPiman2", "TVI_ENVIO_CALIDAD", 
            "TVI_OptimizacionesAsignadas", "TVI_OptiLanzadas", "TVI_HistoricoOptisCabecera", 
            "TVI_CapacidadesMesasCorte", "TVI_AjustesStock", "TVI_Proveedores", 
            "TVI_VISUALCAP_COMENTARIOS", "TVI_InfoContainersLAMI_Log"
        ] 
        
    elif db_name == "FVOptiglass":
        tablas_a_incluir = [
            "Pattern", "PatternLog", "PatternDetail", "Releases", "Remakes", 
            "Machines", "MachineParameters", "GeneralSetup", "Locations", 
            "StockSizes", "StoreSizes", "RackDetail", "Racks", "Part", "uvw_storeSizes"
        ]

    return SQLDatabase(
        engine, 
        #include_tables=tablas_a_incluir,
        sample_rows_in_table_info=1)