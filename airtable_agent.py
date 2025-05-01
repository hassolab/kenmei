import os
from playwright.async_api import async_playwright, TimeoutError
from pyairtable import Api
from dotenv import load_dotenv
import asyncio
import re
import traceback # Import traceback explicitly
import time # Import time for timeout tracking

load_dotenv()

# ... (Airtable setup remains the same) ...
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")

if not all([AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME]):
    raise ValueError("Airtable environment variables not set correctly.")

api = Api(AIRTABLE_API_KEY)
table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

# --- Predicate function for network response wait ---
async def check_image_response(response):
    """Check if the response is the target image signal, requiring 'spark_page' in the URL."""
    content_type = await response.header_value("content-type")
    is_image = content_type and "image" in content_type.lower()
    return (
        "www.genspark.ai" in response.url and 
        "spark_page" in response.url and
        response.request.method == "GET" and 
        response.status == 200 and 
        is_image
    )

async def run_genspark_interaction(empresa, pais, consideraciones, airtable_record_id):
    """
    Runs the full Genspark interaction process based on the specified flow.
    """
    logs = []
    def log_and_print(message):
        print(message) # Print to local terminal
        logs.append(message) # Append for browser logs

    log_and_print("Iniciando run_genspark_interaction...")
    analysis_markdown = None
    success = False

    # Load credentials securely
    email = os.getenv("GENSPARK_EMAIL")
    password = os.getenv("GENSPARK_PASSWORD")
    login_url = os.getenv("GENSPARK_LOGIN_URL") # Make sure this is in your .env

    if not email or not password or not login_url:
        log_and_print("Error CRÍTICO: Faltan credenciales de Genspark o URL de login en el archivo .env")
        return {"success": False, "content": None, "logs": logs}
    log_and_print("Credenciales de Genspark y URL cargadas.")

    # --- Long Query (NO MODIFICAR) ---
    long_query = f"""
Realiza un análisis de la empresa "{empresa}" que radica en "{pais}". Debes tener las siguientes consideraciones: "{consideraciones}". 
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
¿Hay alguna área específica sobre la que crees que sea importante profundizar en este estudio de tendencias?
"""
    



    log_and_print("Query larga preparada.")

    async with async_playwright() as p:
        browser = None
        log_and_print("Inicializando Playwright...")
        try:
            # --- Stealth Options --- 
            # Define a common user agent string
            user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            log_and_print(f"Usando User-Agent: {user_agent}")
            # Script to disable webdriver flag
            stealth_script = "Object.defineProperty(navigator, 'webdriver', {get: () => false})"
            log_and_print("Script para ocultar 'navigator.webdriver' preparado.")
            
            # --- Launch Browser (Headless as Intended) ---
            log_and_print("Lanzando navegador Chromium (MODO HEADLESS)...")
            # browser = await p.chromium.launch(headless=False) # Keep commented unless debugging visually
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox']) # <-- Use headless=True
            log_and_print("Navegador lanzado exitosamente (headless).")
            
            # --- Create Context with Stealth Options ---
            log_and_print("Creando contexto del navegador con User-Agent modificado...")
            context = await browser.new_context(user_agent=user_agent)
            log_and_print("Contexto creado.")
            
            # Grant clipboard permissions proactively
            try:
                await context.grant_permissions(['clipboard-read', 'clipboard-write'])
                log_and_print("Permisos de portapapeles solicitados.")
            except Exception as perm_error:
                 log_and_print(f"Advertencia: No se pudieron establecer permisos de portapapeles (puede fallar la copia): {perm_error}")

            page = await context.new_page()
            page.set_default_timeout(900000) # 15 minutes global timeout
            log_and_print("Nueva página creada y timeout global establecido (15 min).")

            # --- Apply Stealth Script --- 
            log_and_print("Añadiendo script de inicialización para ocultar 'navigator.webdriver'...")
            await page.add_init_script(stealth_script)
            log_and_print("Script añadido.")

            # --- Navigate to Login URL --- 
            log_and_print(f"Navegando a la URL de login: {login_url}")
            await page.goto(login_url)
            log_and_print("Navegación a URL de login completada.")

            # --- First Login Sequence (New Flow) ---
            log_and_print("[Flow 1] Localizando botón 'Login with email'...")
            login_email_button_selector = 'button:has-text("Login with email")'
            await page.locator(login_email_button_selector).wait_for(state="visible", timeout=30000)
            log_and_print("[Flow 2] Haciendo clic en botón 'Login with email'...")
            await page.locator(login_email_button_selector).click()

            log_and_print("[Flow 3] Localizando input[type='email']...")
            email_selector = "input[type='email']"
            await page.locator(email_selector).wait_for(state="visible", timeout=15000)
            log_and_print("[Flow 4] Rellenando input email...")
            await page.locator(email_selector).fill(email)

            log_and_print("[Flow 5] Localizando input[type='password']...")
            password_selector = "input[type='password']"
            await page.locator(password_selector).wait_for(state="visible", timeout=15000)
            log_and_print("[Flow 6] Rellenando input password...")
            await page.locator(password_selector).fill(password)

            log_and_print("[Flow 7] Localizando #next...")
            next_button_selector = "#next" # Keeping ID selector as specified
            await page.locator(next_button_selector).wait_for(state="visible", timeout=15000)
            log_and_print("[Flow 8] Haciendo clic en #next...")
            await page.locator(next_button_selector).click()
            log_and_print("Primer inicio de sesión enviado.")

            log_and_print("[Flow 9] Esperando 3 segundos...")
            await asyncio.sleep(3)

            # --- Modal Interaction (New Flow) ---
            log_and_print("[Flow 10] Buscando SVG dentro de .n-modal...")
            modal_svg_selector = ".n-modal svg"
            try:
                await page.locator(modal_svg_selector).first.wait_for(state="visible", timeout=10000) # Shorter timeout, might not appear
                log_and_print("[Flow 11] Haciendo clic en SVG del modal...")
                await page.locator(modal_svg_selector).first.click()
            except TimeoutError:
                log_and_print("SVG en modal no encontrado o timeout (puede ser normal). Continuando...")

            log_and_print("[Flow 12] Esperando 2 segundos...")
            await asyncio.sleep(2)

            # --- Send "Hola" (New Flow) ---
            log_and_print("[Flow 13] Localizando textarea.search-input...")
            chat_input_selector = "textarea.search-input"
            await page.locator(chat_input_selector).wait_for(state="visible", timeout=30000)
            log_and_print("[Flow 14] Escribiendo 'Hola'...")
            await page.locator(chat_input_selector).fill("Hola")

            log_and_print("[Flow 15] Localizando .enter-icon...")
            send_button_selector = ".enter-icon"
            await page.locator(send_button_selector).wait_for(state="visible", timeout=15000)
            log_and_print("[Flow 16] Haciendo clic en .enter-icon...")
            await page.locator(send_button_selector).click()
            log_and_print("'Hola' enviado.")

            log_and_print("[Flow 17] Esperando 5 segundos...")
            await asyncio.sleep(5)

            # --- Second Login Sequence (Attempt - New Flow) ---
            log_and_print("--- Iniciando segundo intento de login (preventivo) ---")
            try:
                log_and_print("[Flow 18] Buscando botón 'Login with email' de nuevo...")
                if await page.locator(login_email_button_selector).is_visible(timeout=5000):
                    log_and_print("   Elemento encontrado. Haciendo clic...")
                    await page.locator(login_email_button_selector).click()

                    log_and_print("[Flow 20] Buscando input[type='email'] de nuevo...")
                    if await page.locator(email_selector).is_visible(timeout=5000):
                        log_and_print("[Flow 21]    Rellenando input email...")
                        await page.locator(email_selector).fill(email)
                    else:
                        log_and_print("   input email no visible para segundo login.")

                    log_and_print("[Flow 22] Buscando input[type='password'] de nuevo...")
                    if await page.locator(password_selector).is_visible(timeout=5000):
                         log_and_print("[Flow 23]   Rellenando input password...")
                         await page.locator(password_selector).fill(password)
                    else:
                         log_and_print("   input password no visible para segundo login.")

                    log_and_print("[Flow 24] Buscando #next de nuevo...")
                    if await page.locator(next_button_selector).is_visible(timeout=5000):
                         log_and_print("[Flow 25]   Haciendo clic en #next...")
                         await page.locator(next_button_selector).click()
                         log_and_print("   Segundo intento de login enviado.")
                    else:
                         log_and_print("   #next no visible para segundo login.")

                    log_and_print("[Flow 26] Esperando 3 segundos post-segundo intento...")
                    await asyncio.sleep(3)
                else:
                     log_and_print("   Botón 'Login with email' no encontrado, asumiendo que ya estamos logueados.")

            except Exception as e:
                log_and_print(f"   Excepción durante el segundo intento de login (ignorado): {e}")
            log_and_print("--- Fin del segundo intento de login ---")

            log_and_print("[Flow 27] Esperando 5 segundos adicionales...")
            await asyncio.sleep(5)

            # --- Navigate Directly to Deep Research Agent (Replaces old 28-30) ---
            deep_research_url = "https://www.genspark.ai/agents?type=agentic_deep_research"
            log_and_print(f"[Flow 28] Navegando directamente a: {deep_research_url}")
            await page.goto(deep_research_url)
            log_and_print("   Navegación a Deep Research completada.")

            log_and_print("[Flow 29] Esperando 3 segundos...")
            await asyncio.sleep(3)

            # --- Continue with sending query (Old step 31 is now 30) ---
            log_and_print("[Flow 30 - antes 31] Localizando textarea.search-input para query larga...")
            await page.locator(chat_input_selector).wait_for(state="visible", timeout=30000)
            log_and_print("[Flow 31 - antes 32] Escribiendo query larga...")
            await page.locator(chat_input_selector).fill(long_query)

            log_and_print("[Flow 32 - antes 33] Localizando .enter-icon para query larga...")
            await page.locator(send_button_selector).wait_for(state="visible", timeout=15000)
            log_and_print("[Flow 33 - antes 34] Haciendo clic en .enter-icon para enviar query...")
            await page.locator(send_button_selector).click()
            log_and_print("Query larga enviada.")

            # --- Wait for Image Element in DOM (Replaces Network Wait - New 34) ---
            max_wait_time = 900 # seconds (15 minutes)
            poll_interval = 30 # seconds
            start_time = time.time()
            image_found = False
            img_selector = "img" # Base selector
            target_src_substring = "spark_page"

            log_and_print(f"[Flow 34] Iniciando sondeo del DOM cada {poll_interval}s buscando '{img_selector}[src*=\"{target_src_substring}\"]' (max {max_wait_time}s)...")

            while time.time() - start_time < max_wait_time:
                # Find all image elements currently in the DOM
                all_images = page.locator(img_selector)
                count = await all_images.count()
                found_matching_image = False
                if count > 0:
                    log_and_print(f"   Encontrados {count} elementos '{img_selector}'. Verificando atributo src...")
                    for i in range(count):
                        img = all_images.nth(i)
                        try:
                            src = await img.get_attribute("src")
                            if src and target_src_substring in src:
                                log_and_print(f"   ¡Imagen encontrada con '{target_src_substring}' en src!: {src}")
                                image_found = True
                                found_matching_image = True
                                break # Exit the inner for loop
                        except Exception as e:
                            # Log error getting attribute but continue checking other images
                            log_and_print(f"    Advertencia: Error obteniendo src de imagen {i}: {e}")
                    if found_matching_image:
                        break # Exit the outer while loop
                        
                if not image_found:
                    log_and_print(f"   Imagen con '{target_src_substring}' en src no encontrada. Esperando {poll_interval}s para volver a sondear...")
                    await asyncio.sleep(poll_interval)

            if not image_found:
                log_and_print(f"   TIMEOUT: No se encontró ningún elemento '{img_selector}' con '{target_src_substring}' en src después de {max_wait_time}s.")
                raise TimeoutError(f"No se encontró un elemento '{img_selector}' con '{target_src_substring}' en src dentro del tiempo límite.")

            # --- Wait after finding image (New 35) ---
            log_and_print("[Flow 35] Imagen encontrada. Esperando 5 segundos adicionales...")
            await asyncio.sleep(5)

            # --- Copy Result (Old 37/38 is now 36/37) ---
            log_and_print("[Flow 36] Buscando el penúltimo elemento con CLASE .buttons...")
            buttons_selector = ".buttons" # Confirming: Using class selector
            # --- ADDED: Explicit wait for the buttons AFTER the image wait ---
            log_and_print("   Esperando explícitamente a que aparezcan los elementos con CLASE .buttons (Timeout: 60s)...")
            try:
                # Wait for the *last* group of buttons (identified by class) to be visible
                await page.locator(buttons_selector).last.wait_for(state="visible", timeout=60000)
                log_and_print("   Al menos un elemento con CLASE .buttons está visible.")
            except TimeoutError:
                log_and_print(f"   TIMEOUT esperando a que los elementos con CLASE {buttons_selector} estén visibles.")
                # Even if an image appeared, if buttons don't appear, it's an error
                raise Exception(f"Los botones de copia (CLASE {buttons_selector}) no aparecieron después de encontrar una imagen.")

            all_buttons_groups = page.locator(buttons_selector) # Using class selector
            count = await all_buttons_groups.count()
            log_and_print(f"   Encontrados {count} elementos con CLASE .buttons.")

            if count >= 2:
                copy_button_element = all_buttons_groups.nth(-2) # Penúltimo
                log_and_print("[Flow 37] Haciendo clic en el penúltimo elemento con CLASE .buttons (botón de copiar)...")
                # It's often better to click a specific button *inside* the container if possible
                # Try finding a button or svg inside the target container first
                try:
                    copy_button_inner = copy_button_element.locator('button, svg').first
                    await copy_button_inner.click(timeout=5000)
                    log_and_print("   Clic en botón/svg interno realizado.")
                except (TimeoutError, Exception):
                    log_and_print("   No se encontró botón/svg interno, haciendo clic en el contenedor .buttons...")
                    await copy_button_element.click() # Fallback to clicking the container

                log_and_print("   Esperando acción de portapapeles...")
                await asyncio.sleep(1.5) # Give a bit more time for clipboard action

                log_and_print("   Leyendo contenido del portapapeles...")
                # Ensure permissions were granted
                clipboard_content = await page.evaluate('navigator.clipboard.readText()')
                log_and_print(f"   Contenido crudo del portapapeles: {clipboard_content[:200]}...")

                # Process clipboard content (find first #)
                match = re.search(r'#.*', clipboard_content, re.DOTALL)
                if match:
                    analysis_markdown = match.group(0).strip()
                    log_and_print("   Contenido procesado (desde '#').")
                    success = True
                elif clipboard_content: # Use raw content if '#' not found but content exists
                     log_and_print("   ADVERTENCIA: No se encontró '#' en el portapapeles. Usando contenido crudo.")
                     analysis_markdown = clipboard_content.strip()
                     success = True # Still consider success if we got something
                else:
                    log_and_print("   ERROR: No se pudo leer contenido del portapapeles o estaba vacío.")
                    success = False # Mark as failure if clipboard is empty or unreadable

            else:
                log_and_print(f"   ERROR: No se encontraron suficientes ({count}) elementos con CLASE '.buttons' para hacer clic en el penúltimo.")
                success = False # Mark as failure if we couldn't find the button

        except TimeoutError as e:
            log_and_print(f"Error de TIMEOUT durante la automatización: {e}")
            log_and_print(f"   URL actual: {page.url if 'page' in locals() and page else 'N/A'}")
            log_and_print(f"   Traceback: {traceback.format_exc()}")
            success = False
        except Exception as e:
            log_and_print(f"Error EXCEPCIÓN GENERAL durante la automatización: {e}")
            log_and_print(f"   Traceback: {traceback.format_exc()}")
            success = False
        finally:
            # --- Browser Cleanup ---
            log_and_print("Bloque finally alcanzado. Intentando cerrar el navegador si existe...")
            if browser:
                try:
                    if browser.is_connected():
                        log_and_print("   Cerrando navegador...")
                        await browser.close()
                        log_and_print("   Navegador cerrado.")
                    else:
                        log_and_print("   El navegador no estaba conectado (no se necesita cerrar).")
                except Exception as close_err:
                    log_and_print(f"   Error durante el cierre del navegador: {close_err}")
            else:
                log_and_print("   La variable 'browser' era None (probablemente falló el lanzamiento inicial).")

    # --- Airtable Update (Old 39 is now 38) ---
    log_and_print("--- Iniciando actualización de Airtable (si aplica) ---")
    if airtable_record_id:
        if success and analysis_markdown:
            try:
                log_and_print(f"[Flow 38] Actualizando Airtable record {airtable_record_id} con 'Analisis'...")
                table.update(airtable_record_id, {'Analisis': analysis_markdown})
                log_and_print("   Actualización de Airtable exitosa.")
            except Exception as e:
                log_and_print(f"   ERROR al actualizar Airtable (éxito): {e}")
        elif not success:
            try:
                log_and_print(f"[Flow 38 - Fallo] Proceso de automatización falló.")
                # error_details = "\n".join(logs[-5:]) # Get last 5 log messages
                # Consider adding an 'Error Details' field to Airtable and updating it here
                # table.update(airtable_record_id, {'Status': 'Error', 'Error Details': error_details})
                log_and_print("   (No se actualizó ningún campo de error en Airtable para evitar fallos).")
            except Exception as e:
                log_and_print(f"   ERROR al intentar marcar Airtable como Error: {e}")
    else:
         log_and_print("   No hay record_id de Airtable, omitiendo actualización.")

    log_and_print("Fin de run_genspark_interaction.")
    return {"success": success, "content": analysis_markdown, "logs": logs}

# --- Airtable Helper Functions (Keep create_airtable_record as is) ---
def create_airtable_record(empresa, pais, consideraciones):
    """Creates an initial Airtable record and returns its ID and an error message if applicable."""
    try:
        record = table.create({
            'Empresa': empresa,
            'Pais': pais,
            'Consideraciones': consideraciones
            # Removed 'Status': 'Procesando'
        })
        print(f"Created Airtable record {record['id']}")
        return record['id'], None
    except Exception as e:
        print(f"Error creating Airtable record: {e}")
        error_message = f"Error de Airtable al crear registro: {e}"
        return None, error_message

# Example usage (for testing script directly)
# if __name__ == "__main__":
#     test_empresa = "Bimbo"
#     test_pais = "México"
#     test_consideraciones = "Foco en reducción de azúcares y uso de granos enteros."
#     test_record_id = create_airtable_record(test_empresa, test_pais, test_consideraciones)
#     if test_record_id:
#         result = asyncio.run(run_genspark_interaction(test_empresa, test_pais, test_consideraciones, test_record_id))
#         print("\n--- RESULT ---")
#         print(f"Success: {result['success']}")
#         print(f"Content (first 200 chars): {result.get('content', '')[:200]}...")
#         print("\n--- LOGS ---")
#         for log_msg in result.get('logs', []):
#              print(log_msg)
