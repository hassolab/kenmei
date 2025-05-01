# filename: app.py
import asyncio
import os
import traceback
# Remove direct Playwright imports if not used elsewhere in app.py
# from playwright.async_api import async_playwright, TimeoutError 
from dotenv import load_dotenv
from pyairtable import Api
from flask import Flask, render_template, request, jsonify
import html # Import html module for escaping
import markdown # Ensure markdown library is installed

# ---> Import functions from airtable_agent <--- 
from airtable_agent import run_genspark_interaction, create_airtable_record

# --- Flask App Setup ---
app = Flask(__name__)

# --- Load Environment Variables ---
load_dotenv() # Load variables from .env file

# Genspark Credentials (kept here for potential direct use or moved to agent)
email = os.getenv("GENSPARK_EMAIL")
password = os.getenv("GENSPARK_PASSWORD")

# Airtable Credentials (needed for create_airtable_record if called directly from Flask)
airtable_api_key = os.getenv("AIRTABLE_API_KEY")
airtable_base_id = os.getenv("AIRTABLE_BASE_ID")
# Table name can be defined here or within the agent function
# airtable_table_name = "AnalisisInicial"

# --- Check Credentials --- #
CREDENTIALS_ERROR = None
# Check only credentials needed directly by app.py (Airtable for initial creation)
if not airtable_api_key or not airtable_base_id:
    CREDENTIALS_ERROR = "Error Critico: Faltan credenciales de Airtable en el archivo .env. Revisa AIRTABLE_API_KEY, AIRTABLE_BASE_ID."
    print(CREDENTIALS_ERROR)
# Genspark check is handled within run_genspark_interaction


# --- REMOVED run_genspark_interaction function definition from here ---
# The entire async def run_genspark_interaction(...) block is deleted.


# --- Flask Routes --- 
@app.route('/')
def index():
    """Serves the main form page."""
    # Check credentials before rendering page
    if CREDENTIALS_ERROR:
         # You might want a dedicated error template
         return f"<h1>Error de Configuración</h1><p>{CREDENTIALS_ERROR}</p>", 500
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
async def submit():
    """Handles form submission, creates initial Airtable record, runs automation, updates record."""
    if CREDENTIALS_ERROR: # Check for Airtable credential errors
        return jsonify({"status": "error", "message": CREDENTIALS_ERROR, "logs": [CREDENTIALS_ERROR]}), 500

    if not request.is_json:
        return jsonify({"error": "Request must be JSON", "logs": ["Error: Request must be JSON"]}), 400

    data = request.get_json()
    empresa = data.get('empresa')
    pais = data.get('pais')
    consideraciones = data.get('consideraciones')

    if not all([empresa, pais, consideraciones]):
        return jsonify({"error": "Faltan datos en el formulario", "logs": ["Error: Faltan datos en el formulario"]}), 400

    request_logs = [] # Initialize logs for this request
    request_logs.append(f"Recibida solicitud: Empresa={empresa}, Pais={pais}, Consideraciones={consideraciones}")

    record_id = None # To store the ID of the initially created record
    # Initialize response data for errors before interaction
    response_data = {"status": "error", "message": "El proceso falló antes de la interacción.", "logs": request_logs}

    try:
        # --- Step 1: Create Initial Airtable Record --- 
        # Uses the imported create_airtable_record function
        request_logs.append("Creando registro inicial en Airtable...")
        record_id, airtable_error = create_airtable_record(empresa, pais, consideraciones)

        if not record_id:
             # Log the detailed error message returned by the function
             log_msg = f"Error crítico al crear registro Airtable: {airtable_error}"
             request_logs.append(log_msg)
             response_data = {"status": "error", "message": airtable_error or "Error desconocido al crear registro inicial en Airtable.", "logs": request_logs}
             return jsonify(response_data), 500
        
        # If successful, continue logging
        request_logs.append(f"Registro inicial creado con ID: {record_id}")

        # --- Step 2: Run Playwright Automation --- 
        # Calls the imported run_genspark_interaction function
        request_logs.append("Iniciando la interacción principal con Genspark...")
        # Note: We don't need to pass email/password if the function reads them from os.getenv()
        interaction_result = await run_genspark_interaction(
            empresa, pais, consideraciones, record_id
        )
        
        # Combine logs
        backend_logs = interaction_result.get("logs", [])
        all_logs = request_logs + backend_logs

        # --- Step 3: Prepare Response based on interaction_result --- 
        if interaction_result["success"]:
            all_logs.append("Proceso completado exitosamente.") # Add final success log
            response_data = {
                "status": "success",
                "message": "Generación de reporte finalizada.",
                "analysis_markdown": interaction_result["content"],
                "logs": all_logs
            }
        else:
            # Handle failure case from the agent
            error_msg = "Error durante la generación del reporte." 
            # Try to get more specific error from logs if available
            if backend_logs:
                 error_msg += f" Último log: {backend_logs[-1]}"
            all_logs.append(f"El proceso falló: {error_msg}") # Add final failure log
            response_data = {
                "status": "error",
                "message": error_msg,
                "analysis_markdown": None,
                "logs": all_logs
            }
            # Decide if 500 is appropriate for agent failure vs internal server error
            return jsonify(response_data), 500 

        return jsonify(response_data)

    except Exception as e:
        print(f"Error EXCEPCIÓN GENERAL en ruta /submit: {e}")
        print(traceback.format_exc())
        error_prefix = f"(Record ID: {record_id}) " if record_id else ""
        # Append exception to logs if possible
        request_logs.append(f"Error interno del servidor: {e}")
        response_data = {"status": "error", "message": f"{error_prefix}Error interno del servidor: {e}", "logs": request_logs}
        return jsonify(response_data), 500

# --- Main Execution ---
if __name__ == "__main__":
    # Note: Flask's default development server is not ideal for production
    # or heavy async tasks. Consider using a proper ASGI server like uvicorn or hypercorn.
    print("Starting Flask app...")
    if CREDENTIALS_ERROR:
        print("\n !!! WARNING: AIRTABLE CREDENTIALS ARE MISSING OR INCORRECT IN .env FILE !!!")
        print(" !!! FLASK WILL RUN, BUT SUBMISSIONS WILL FAIL. !!!\n")
    print("Access the agent at http://127.0.0.1:5000")
    app.run(debug=True) # debug=True helps with development, remove for production 