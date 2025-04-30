# filename: app.py
import asyncio
import os
import traceback
from playwright.async_api import async_playwright, TimeoutError
from dotenv import load_dotenv
from pyairtable import Api
from flask import Flask, render_template, request, jsonify
import html # Import html module for escaping

# --- Flask App Setup ---
app = Flask(__name__)

# --- Load Environment Variables ---
load_dotenv() # Load variables from .env file

# Genspark Credentials
email = os.getenv("GENSPARK_EMAIL")
password = os.getenv("GENSPARK_PASSWORD")

# Airtable Credentials
airtable_api_key = os.getenv("AIRTABLE_API_KEY")
airtable_base_id = os.getenv("AIRTABLE_BASE_ID")
airtable_table_name = "AnalisisInicial" # Store table name

# --- Check Credentials --- #
CREDENTIALS_ERROR = None
if not email or not password or not airtable_api_key or not airtable_base_id:
    CREDENTIALS_ERROR = "Error Critico: Faltan credenciales en el archivo .env. Revisa GENSPARK_EMAIL, GENSPARK_PASSWORD, AIRTABLE_API_KEY, AIRTABLE_BASE_ID."
    print(CREDENTIALS_ERROR)

# --- Playwright Interaction Logic (Modified Return Value) ---
async def run_genspark_interaction(loaded_email, loaded_password, empresa, pais, consideraciones):
    # Define the base query template
    base_query_template = """Realiza un análisis de la empresa {empresa} que radica en {pais}. Debes tener las siguientes consideraciones: {consideraciones}.
El estudio que hagas debe responder cada una de estas preguntas:
¿Cuál es el sector o industria específica de la marca o empresa?
¿Cuáles son los principales productos o servicios que ofrece actualmente?
¿Cuál es su público objetivo (segmentación demográfica y psicográfica)?
¿Cuáles son sus principales competidores en el mercado?
¿Identificas algún cambio significativo en el comportamiento de compra de los clientes de la marca recientemente?
¿Qué tendencias identificas en el corto, medio o largo plazo que puedan impactar a la empresa?
¿Qué tendencias tecnológicas crees que podrían afectar al sector de esa marca en los próximos años?
¿Detectas alguna tendencia social o cultural emergente que consideres relevante para la marca?
¿Qué canales de distribución y comunicación utiliza actualmente?
¿Cuáles consideras que son los indicadores clave de rendimiento (KPIs) más importantes para evaluar el éxito de esa marca?
¿Existe alguna regulación o cambio legislativo que pueda impactar su industria próximamente?
¿Qué factores económicos están afectando o podrían afectar a su mercado?
¿Cuáles consideras son sus objetivos estratégicos para los próximos 12-24 meses?
¿Hay alguna área específica sobre la que crees que sea importante profundizar en este estudio de tendencias?"""

    # Format the query dynamically
    long_query = base_query_template.format(empresa=empresa, pais=pais, consideraciones=consideraciones)
    print("--- Generated Query ---")
    print(long_query)
    print("-----------------------")

    # Default return structure for errors before completion
    result_data = {"status": "error", "message": "Script execution did not complete."}

    async with async_playwright() as p:
        browser = None # Initialize browser variable
        try:
            browser = await p.chromium.launch(headless=True) # Headed for debugging
            # browser = await p.chromium.launch(headless=True) # Headless for server
            context = await browser.new_context()
            page = await context.new_page()
            page.set_default_timeout(900000) # 15 minutes

            # --- Check if credentials loaded --- (Added check inside function)
            if not loaded_email or not loaded_password or not airtable_api_key or not airtable_base_id:
                 raise ValueError("Credenciales faltantes. Revisa el archivo .env y reinicia la aplicación.")

            print("Navigating to Genspark Login Page...")
            login_url = "https://login.genspark.ai/gensparkad.onmicrosoft.com/b2c_1_new_login/oauth2/v2.0/authorize?client_id=536a4e98-fd24-4cbc-a67b-417e209e0080&response_type=code&redirect_uri=https%3A%2F%2Fwww.genspark.ai%2Fapi%2Fauth&scope=email+offline_access+openid+profile&state=FIWtZzPVhUjOYSCw&code_challenge=_fXrdW71S7fggK14GiGhxrXbYGNyAkPl6ebj0wuuljs&code_challenge_method=S256&nonce=dad2cf5777cd93867b2964223c01afd49b1d01b22db4900fd15d6e3ede879be3&client_info=1"
            await page.goto(login_url)
            await page.wait_for_load_state('networkidle')

            # --- First Login Sequence ---
            print("[Step 1] Looking for 'Login with email' button...")
            login_email_button_selector = 'button:has-text("Login with email")'
            await page.locator(login_email_button_selector).first.click()
            print("Clicked 'Login with email'.")

            print("[Step 2] Waiting 2 seconds...")
            await asyncio.sleep(2)

            print("[Step 3/4] Locating and filling email...")
            email_input_selector = 'input[type="email"]'
            await page.wait_for_selector(email_input_selector)
            await page.locator(email_input_selector).fill(loaded_email)
            print("Email entered.")

            print("[Step 5/6] Locating and filling password...")
            password_input_selector = 'input[type="password"]'
            await page.wait_for_selector(password_input_selector)
            await page.locator(password_input_selector).fill(loaded_password)
            print("Password entered.")

            print("[Step 7] Looking for 'Sign in' button...")
            login_submit_button_selector = 'button:has-text("Sign in"), button[type="submit"]'
            await page.locator(login_submit_button_selector).first.click()
            print("Clicked 'Sign in'.")

            print("[Step 8] Waiting 2 seconds after first sign in...")
            await asyncio.sleep(2)

            print("[Step 9/10] Looking for SVG in modal and clicking it...")
            modal_svg_selector = ".n-modal svg"
            try:
                await page.wait_for_selector(modal_svg_selector, timeout=15000)
                await page.locator(modal_svg_selector).first.click()
                print("Clicked SVG in modal.")
            except TimeoutError:
                print("Modal SVG not found or timed out. Skipping this step.")

            print("[Step 11] Waiting 1 second...")
            await asyncio.sleep(1)

            print("[Step 12] Typing 'Hola' in chat and pressing Enter...")
            chat_input_selector = 'textarea'
            try:
                 await page.wait_for_selector(chat_input_selector, timeout=15000)
                 chat_input = page.locator(chat_input_selector).first
                 await chat_input.fill("Hola")
                 await chat_input.press('Enter')
                 print("Message 'Hola' sent.")
            except TimeoutError:
                 print("Chat textarea not found after first login. Cannot send 'Hola'.")

            print("[Step 13] Waiting 5 seconds (potential redirection)...")
            await asyncio.sleep(5)
            print("Current URL after 5s wait:", page.url)

            # --- Second Login Sequence (Attempt) ---
            print("\n--- Starting Second Login Sequence (Attempt) ---")
            try:
                print("[Step 14] Looking for 'Login with email' button again...")
                # Use a shorter timeout here, if it's not there quickly, we assume logged in
                await page.locator(login_email_button_selector).first.click(timeout=5000)
                print("Clicked 'Login with email' again.")

                print("[Step 15] Waiting 2 seconds...")
                await asyncio.sleep(2)

                print("[Step 16/17] Locating and filling email again...")
                if await page.locator(email_input_selector).is_visible(timeout=5000):
                     await page.locator(email_input_selector).fill(loaded_email)
                     print("Email entered again.")
                else:
                     print("Email input not found/visible for second login attempt. Skipping.")

                print("[Step 18/19] Locating and filling password again...")
                if await page.locator(password_input_selector).is_visible(timeout=5000):
                    await page.locator(password_input_selector).fill(loaded_password)
                    print("Password entered again.")
                else:
                    print("Password input not found/visible for second login attempt. Skipping.")

                print("[Step 20] Looking for 'Sign in' button again...")
                if await page.locator(login_submit_button_selector).first.is_visible(timeout=5000):
                     await page.locator(login_submit_button_selector).first.click()
                     print("Clicked 'Sign in' again.")
                else:
                      print("Sign in button not found/visible for second login attempt. Skipping.")

                print("[Step 21] Waiting 2 seconds after second sign in attempt...")
                await asyncio.sleep(2)

            except Exception as e:
                print(f"Second login sequence skipped or failed (maybe already logged in?): {e}")
                print("Attempting to continue assuming login state is correct...")

            print("Current URL before main task:", page.url)

            # --- Main Task Sequence ---
            print("\n--- Starting Main Task Sequence ---")

            print("[Step 22/23] Looking for and clicking 'Investigación Profunda'...")
            investigacion_selector = 'div.title:has-text("Investigación Profunda")'
            try:
                # Wait longer here as the main page might take time to load
                await page.wait_for_selector(investigacion_selector, timeout=30000)
                await page.locator(investigacion_selector).first.click()
                print("Clicked 'Investigación Profunda'.")
            except TimeoutError:
                 print("'Investigación Profunda' element not found.")
                 raise Exception("'Investigación Profunda' element not found, cannot proceed.")

            print("[Step 24] Waiting 5 seconds...")
            await asyncio.sleep(5)

            print("[Step 25/26] Entering long query in chat and pressing Enter...")
            try:
                 await page.wait_for_selector(chat_input_selector, timeout=15000)
                 chat_input = page.locator(chat_input_selector).first
                 await chat_input.fill(long_query)
                 await chat_input.press('Enter')
                 print("Long query sent.")
            except TimeoutError:
                 print("Chat textarea not found for long query.")
                 raise Exception("Chat input not found for long query, cannot proceed.")

            # --- Wait for specific image response ---
            print("[NEW Step 26a] Waiting for specific image network response (up to 15 minutes)...")
            try:
                await page.wait_for_event(
                    "response",
                    lambda response: (
                        "www.genspark.ai" in response.url and
                        response.request.method == "GET" and
                        response.status == 200 and
                        response.request.resource_type == "image"
                    ),
                    timeout=900000 # Use the updated 15-minute timeout
                )
                print("[NEW Step 26b] Target image response detected.")
            except TimeoutError:
                print("[NEW Step 26b] TIMEOUT: Target image response not detected within 15 minutes.")
                raise Exception("Timeout waiting for the specific image response signal.")
            # --- END: Wait for specific image response ---

            # Step 27/28: Find and click second-to-last ".buttons" element
            print("[Step 27/28] Looking for second-to-last '.buttons' element and clicking it...")
            buttons_selector = ".buttons"
            try:
                all_buttons = page.locator(buttons_selector)
                count = await all_buttons.count()
                if count >= 2:
                    second_last_button = all_buttons.nth(-2)
                    await second_last_button.wait_for(state='visible', timeout=10000)
                    await second_last_button.click()
                    print("Clicked the second-to-last '.buttons' element (likely copy button).")
                elif count == 1:
                    print("Found only 1 '.buttons' element. Clicking it instead.")
                    last_button = all_buttons.last
                    await last_button.wait_for(state='visible', timeout=10000)
                    await last_button.click()
                    print("Clicked the last '.buttons' element.")
                else:
                    raise Exception(f"Could not find suitable '.buttons' element ({count} found) to click.")
            except TimeoutError:
                print(f"Timed out waiting for '{buttons_selector}' element.")
                raise Exception("Copy button not found or timed out.")
            except Exception as e:
                 print(f"Error clicking the copy button: {e}")
                 raise e

            # Step 29: Attempting to read clipboard
            print("[Step 29] Attempting to read clipboard...")
            await asyncio.sleep(1)
            processed_clipboard_content = None # Initialize to None
            raw_clipboard_content = ""
            try:
                await context.grant_permissions(['clipboard-read', 'clipboard-write'])
                raw_clipboard_content = await page.evaluate('navigator.clipboard.readText()')
                print("Successfully read clipboard.")
                print("Processing clipboard content to find first '#'...")
                try:
                    first_hash_index = raw_clipboard_content.index('#')
                    processed_clipboard_content = raw_clipboard_content[first_hash_index:].strip()
                    print("Content processed. Starting from first '#'.")
                    # Success Case: Return processed content
                    result_data = {"status": "success", "content": processed_clipboard_content}
                except ValueError:
                    print("Warning: '#' not found in clipboard content. Using original content.")
                    processed_clipboard_content = raw_clipboard_content.strip()
                    # Still consider this success, but maybe log differently or flag?
                    result_data = {"status": "success_no_hash", "content": processed_clipboard_content}
            except Exception as e:
                print(f"Error reading clipboard: {e}")
                result_data = {"status": "error", "message": f"Error reading clipboard: {e}"}

        except TimeoutError as e:
            print(f"A timeout occurred during the process: {e}")
            result_data = {"status": "error", "message": f"Error: Tiempo de espera agotado: {e}"}
        except ValueError as e: # Catch specific credential error
             print(f"Error de Configuración: {e}")
             result_data = {"status": "error", "message": f"Error de Configuración: {e}"}
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            print(traceback.format_exc())
            result_data = {"status": "error", "message": f"Error inesperado: {e}"}
        finally:
            print("\nClosing browser...")
            # Avoid closing the browser if it's already closed due to an error
            if 'browser' in locals() and browser.is_connected():
                await browser.close()

        return result_data # Return the dictionary

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
    if CREDENTIALS_ERROR:
        return jsonify({"status": "error", "message": CREDENTIALS_ERROR}), 500

    record_id = None # To store the ID of the initially created record
    # Initialize response data for errors before interaction
    response_data = {"status": "error", "message": "El proceso falló antes de la interacción."} 

    try:
        empresa = request.form['empresa']
        pais = request.form['pais']
        consideraciones = request.form['consideraciones']
        print(f"Received submission: Empresa={empresa}, Pais={pais}, Consideraciones={consideraciones}")

        # --- Step 1: Create Initial Airtable Record ---
        print("Attempting to create initial Airtable record...")
        try:
            api = Api(airtable_api_key)
            table = api.table(airtable_base_id, airtable_table_name)
            initial_data = {
                'Empresa': empresa,
                'Pais': pais,
                'Consideraciones': consideraciones
                # 'Analisis' field is left empty initially
            }
            create_response = table.create(initial_data)
            record_id = create_response['id']
            print(f"Initial Airtable record created: ID {record_id}")
        except Exception as e:
            print(f"Error creating initial Airtable record: {e}")
            # Return error immediately if initial creation fails
            response_data = {"status": "error", "message": f"Error al crear registro inicial en Airtable: {e}"}
            return jsonify(response_data), 500

        # --- Step 2: Run Playwright Automation ---
        print(f"Starting Playwright interaction for record ID: {record_id}")
        interaction_result = await run_genspark_interaction(
            email, password, empresa, pais, consideraciones
        )

        # --- Step 3: Update Airtable Record & Prepare Response ---
        if interaction_result["status"].startswith("success") and "content" in interaction_result:
            analysis_content = interaction_result["content"]
            print(f"Playwright interaction successful. Updating Airtable record {record_id}...")
            try:
                # Reconnect API and Table (good practice in case of long delays)
                api = Api(airtable_api_key)
                table = api.table(airtable_base_id, airtable_table_name)
                update_data = {
                    'Analisis': analysis_content
                }
                table.update(record_id, update_data)
                print(f"Airtable record {record_id} updated successfully.")
                
                # Prepare success response with RAW Markdown content
                response_data = {
                    "status": "success",
                    "message": "Generación de reporte finalizada.", # Simplified message
                    "analysis_markdown": analysis_content # Send raw content for JS rendering
                }

            except Exception as e:
                print(f"Error updating Airtable record {record_id}: {e}")
                # Report success in generation but error in saving update
                response_data = {
                    "status": "error", 
                    "message": f"Generación completada pero error al actualizar Airtable (ID: {record_id}): {e}. Intenta revisar el registro manualmente."
                    # Optionally include analysis_html here if useful despite saving error
                }
        else:
            # Handle case where Playwright interaction failed
            error_msg = interaction_result.get("message", "Error desconocido en la automatización.")
            print(f"Playwright interaction failed: {error_msg}")
            response_data = {"status": "error", "message": f"Automatización fallida: {error_msg}. Se creó un registro inicial en Airtable (ID: {record_id}) pero no se pudo completar el análisis."}

        return jsonify(response_data)

    except Exception as e:
        print(f"Error in /submit route: {e}")
        print(traceback.format_exc())
        # Include record_id in error if available
        error_prefix = f"(Record ID: {record_id}) " if record_id else ""
        # Ensure error response format is consistent
        response_data = {"status": "error", "message": f"{error_prefix}Error interno del servidor: {e}"}
        return jsonify(response_data), 500

# --- Main Execution ---
if __name__ == "__main__":
    # Note: Flask's default development server is not ideal for production
    # or heavy async tasks. Consider using a proper ASGI server like uvicorn or hypercorn.
    print("Starting Flask app...")
    if CREDENTIALS_ERROR:
        print("\n !!! WARNING: CREDENTIALS ARE MISSING OR INCORRECT IN .env FILE !!!")
        print(" !!! FLASK WILL RUN, BUT SUBMISSIONS WILL FAIL. !!!\n")
    print("Access the agent at http://127.0.0.1:5000")
    app.run(debug=True) # debug=True helps with development, remove for production 