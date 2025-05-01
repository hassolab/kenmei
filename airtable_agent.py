import os
from playwright.async_api import async_playwright
from pyairtable import Api
from dotenv import load_dotenv
import asyncio
import re

load_dotenv()

# ... (Airtable setup remains the same) ...
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")

if not all([AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME]):
    raise ValueError("Airtable environment variables not set correctly.")

api = Api(AIRTABLE_API_KEY)
table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)


async def run_genspark_interaction(empresa, pais, consideraciones, airtable_record_id):
    """
    Runs the full Genspark interaction process.

    Args:
        empresa: Company name.
        pais: Country name.
        consideraciones: Specific considerations.
        airtable_record_id: The ID of the Airtable record to update.

    Returns:
        A dictionary containing:
        - success (bool): True if the process completed successfully, False otherwise.
        - content (str | None): The processed analysis text if successful, None otherwise.
        - logs (list): A list of log messages generated during execution.
    """
    logs = []
    logs.append("Iniciando interacción con Genspark...")
    analysis_markdown = None
    success = False

    # Load credentials securely
    email = os.getenv("GENSPARK_EMAIL")
    password = os.getenv("GENSPARK_PASSWORD")
    login_url = os.getenv("GENSPARK_LOGIN_URL") # Make sure this is in your .env

    if not email or not password or not login_url:
        logs.append("Error: Faltan credenciales de Genspark o URL de login en el archivo .env")
        return {"success": False, "content": None, "logs": logs}

    long_query = f"""
Actua como consultor estratégico experto en análisis de mercados internacionales y tendencias de consumo saludable. Realiza una "Investigación Profunda" sobre la empresa "{empresa}" en "{pais}", considerando específicamente: "{consideraciones}".

Tu análisis debe estructurarse de la siguiente manera:

# 1. Resumen Ejecutivo:
   - Breve descripción de "{empresa}" y su posición actual en "{pais}".
   - Principales hallazgos sobre su alineación con tendencias de consumo saludable y las consideraciones específicas mencionadas.
   - Conclusión clave sobre oportunidades o riesgos.

# 2. Análisis de Mercado y Tendencias en "{pais}":
   - Panorama general del mercado de alimentos/bebidas en "{pais}".
   - Tendencias clave de consumo saludable (ej. orgánico, plant-based, bajo en azúcar, funcional, local).
   - Segmentación de consumidores relevantes para "{empresa}" y las consideraciones.

# 3. Análisis de "{empresa}" en "{pais}":
   - Portafolio de productos actual y su percepción en relación a la salud.
   - Estrategias de marketing y comunicación sobre salud y bienestar.
   - Posicionamiento frente a competidores clave en el segmento saludable.
   - Cumplimiento regulatorio relevante (etiquetado, ingredientes).
   - Iniciativas de sostenibilidad y RSE relacionadas.

# 4. Evaluación frente a Consideraciones Específicas ("{consideraciones}"):
   - Análisis detallado de cómo "{empresa}" aborda (o no) cada punto de las consideraciones.
   - Identificación de brechas o áreas de mejora.

# 5. Oportunidades Estratégicas:
   - Nuevos nichos de mercado o segmentos de consumidores.
   - Innovación de productos o reformulación (más saludables).
   - Estrategias de comunicación y marketing enfocadas en salud.
   - Posibles alianzas o adquisiciones.

# 6. Riesgos y Desafíos:
   - Cambios regulatorios futuros.
   - Competencia creciente en el espacio saludable.
   - Riesgos reputacionales (greenwashing, etc.).
   - Desafíos operativos o de cadena de suministro para productos saludables.

# 7. Conclusiones y Recomendaciones Clave:
   - Síntesis de los hallazgos más importantes.
   - Recomendaciones estratégicas accionables y priorizadas para "{empresa}" en "{pais}", enfocadas en capitalizar las tendencias saludables y abordar las consideraciones específicas.

Utiliza un tono profesional y basado en datos (aunque simulados o inferidos si no tienes acceso directo). Asegúrate de que la estructura sea clara y siga los encabezados solicitados.
"""

    async with async_playwright() as p:
        browser = None # Initialize browser to None
        logs.append("Inicializando Playwright...")
        try:
            # Attempt to launch the browser
            logs.append("Lanzando navegador Chromium (headless, no-sandbox)...")
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            logs.append("Navegador lanzado exitosamente.")

            page = await browser.new_page()
            page.set_default_timeout(900000) # 15 minutes global timeout
            logs.append("Nueva página creada y timeout establecido.")

            logs.append(f"Navegando a la URL de login: {login_url}")
            await page.goto(login_url)

            logs.append("Esperando y haciendo clic en 'Login with email'")
            await page.locator('button:has-text("Login with email")').click()

            logs.append("Ingresando email")
            await page.locator('input[name="email"]').fill(email)
            await page.locator('button[type="submit"]:has-text("Continue")').click() # Assuming a continue button appears

            logs.append("Ingresando contraseña")
            await page.locator('input[name="password"]').fill(password) # Wait for password field implicitly

            logs.append("Haciendo clic en 'Sign in'")
            await page.locator('button[type="submit"]:has-text("Sign in")').click()

            logs.append("Login exitoso, esperando posible modal o carga de página...")
            # Wait for a known element that appears after login, e.g., the chat input area
            # Adjust selector as needed
            chat_input_selector = 'textarea[placeholder*="Send a message"]'
            await page.locator(chat_input_selector).wait_for(state="visible", timeout=60000) # Wait 1 min for chat input
            logs.append("Chat input visible.")

            # --- Interaction flow ---
            # 1. Click SVG in modal (Assuming modal appears and needs closing/interaction)
            #    This step might need adjustment if no modal appears or the selector is different.
            #    Let's assume for now we skip if not immediately visible.
            # svg_selector = 'div[role="dialog"] svg' # Example selector
            # try:
            #     logs.append("Intentando hacer clic en SVG dentro del modal...")
            #     await page.locator(svg_selector).click(timeout=5000) # Short timeout for optional element
            #     logs.append("Clic en SVG realizado.")
            # except Exception as e:
            #     logs.append(f"No se encontró o no se pudo hacer clic en SVG (puede ser normal): {e}")
            #     pass

            # 2. Send "Hola"
            logs.append("Enviando 'Hola' al chat")
            await page.locator(chat_input_selector).fill("Hola")
            await page.keyboard.press("Enter")
            await asyncio.sleep(2) # Short wait after sending

            # 3. Wait 5 seconds (potential redirect/load, though might be handled by subsequent waits)
            # logs.append("Esperando 5 segundos...")
            # await asyncio.sleep(5)

            # 4. Attempt second login sequence (Conditional - only if needed)
            #    This seems unlikely to be necessary if the first login persists.
            #    Skipping for now unless explicitly required.
            # logs.append("Omitiendo segundo intento de login (generalmente no necesario)")

            # 5. Click "Investigación Profunda"
            #    Wait for the element to be visible before clicking
            investigacion_selector = 'button:has-text("Investigación Profunda")' # Adjust if needed
            try:
                logs.append("Esperando por 'Investigación Profunda'")
                await page.locator(investigacion_selector).wait_for(state="visible", timeout=30000) # 30 sec wait
                logs.append("Haciendo clic en 'Investigación Profunda'")
                await page.locator(investigacion_selector).click()
            except Exception as e:
                 logs.append(f"Error al hacer clic en 'Investigación Profunda': {e}. Intentando enviar query directamente.")
                 # Decide if we should proceed or fail here. Let's try proceeding.

            # 6. Send the long query
            logs.append("Enviando la consulta larga...")
            await page.locator(chat_input_selector).fill(long_query)
            await page.keyboard.press("Enter")
            logs.append("Consulta larga enviada.")

            # 7. Wait for specific network response (Image GET request)
            logs.append("Esperando la respuesta de red específica (imagen)...")
            try:
                async with page.expect_response(
                    lambda response: "www.genspark.ai" in response.url and response.request.method == "GET" and response.status == 200 and "image" in response.header_value("content-type").lower(),
                    timeout=900000 # 15 minutes timeout for this specific wait
                ) as response_info:
                    logs.append(f"Respuesta de imagen recibida: {await response_info.value.status} {await response_info.value.url}")
                logs.append("Respuesta de red de imagen detectada.")
            except Exception as e:
                logs.append(f"Timeout o error esperando la respuesta de red de imagen: {e}")
                raise # Re-raise the exception to stop the process if the crucial response didn't arrive

            # 8. Click the second-to-last ".buttons" element (Copy Button)
            buttons_selector = ".buttons" # This might be too generic, refine if possible
            logs.append(f"Esperando y buscando botones con selector: {buttons_selector}")
            await page.locator(buttons_selector).last.wait_for(state="visible", timeout=30000) # Wait for last button group
            all_buttons_groups = await page.locator(buttons_selector).all()
            logs.append(f"Encontrados {len(all_buttons_groups)} grupos de botones.")

            if len(all_buttons_groups) >= 2:
                copy_button_group = all_buttons_groups[-2] # Second to last
                # Try to find a button within this group, often an SVG or button tag
                # Adjust inner selector based on actual structure
                copy_button = copy_button_group.locator('button, svg').first
                logs.append("Intentando hacer clic en el botón de copiar (segundo al último grupo .buttons)...")
                await copy_button.click()
                logs.append("Clic en botón de copiar realizado.")
                await asyncio.sleep(1) # Brief pause for clipboard action
            else:
                logs.append("No se encontraron suficientes elementos '.buttons' para hacer clic en el penúltimo.")
                raise ValueError("No se encontró el botón de copiar esperado.")

            # 9. Read clipboard content
            logs.append("Leyendo contenido del portapapeles...")
            clipboard_content = await page.evaluate('() => navigator.clipboard.readText()')
            logs.append(f"Contenido crudo del portapapeles: {clipboard_content[:200]}...") # Log first 200 chars

            # 10. Process clipboard content
            match = re.search(r'#.*', clipboard_content, re.DOTALL)
            if match:
                analysis_markdown = match.group(0)
                logs.append("Contenido procesado y extraído (a partir del primer '#').")
                logs.append(f"Contenido procesado: {analysis_markdown[:200]}...") # Log first 200 chars
                success = True
            else:
                logs.append("No se encontró el patrón '#' en el contenido del portapapeles. Usando contenido crudo.")
                # Fallback or specific handling needed? Using raw content might work.
                analysis_markdown = clipboard_content # Use raw content as fallback
                if analysis_markdown: # Consider it a success if we got *something*
                    success = True
                else:
                     logs.append("Error: El portapapeles estaba vacío o no se pudo leer.")
                     success = False # Mark as failure if clipboard is empty

        except Exception as e:
            logs.append(f"Error EXCEPCIÓN PRINCIPAL durante la automatización con Playwright: {e}")
            import traceback
            logs.append(f"Traceback: {traceback.format_exc()}")
            success = False # Ensure success is false on any exception
        finally:
            logs.append("Bloque finally alcanzado. Intentando cerrar el navegador si existe...")
            if browser:
                try:
                    if browser.is_connected():
                        logs.append("Cerrando navegador...")
                        await browser.close()
                        logs.append("Navegador cerrado.")
                    else:
                         logs.append("El navegador no estaba conectado, no se necesita cerrar explícitamente (o ya se cerró).")
                except Exception as close_err:
                     logs.append(f"Error durante el cierre del navegador: {close_err}")
            else:
                logs.append("La variable 'browser' era None, no se intentó cerrar (probablemente falló el lanzamiento inicial).")

    # Update Airtable outside the 'finally' block, only if we have an ID
    if airtable_record_id:
        if success and analysis_markdown:
            try:
                logs.append(f"Actualizando registro de Airtable {airtable_record_id} con el análisis.")
                table.update(airtable_record_id, {'Analisis': analysis_markdown, 'Status': 'Completado'})
                logs.append("Registro de Airtable actualizado exitosamente.")
            except Exception as e:
                logs.append(f"Error al actualizar Airtable: {e}")
                # Even if Airtable fails, the core interaction might have succeeded
                # Decide if this should make overall success False
        elif not success:
             try:
                logs.append(f"Actualizando registro de Airtable {airtable_record_id} a estado 'Error'.")
                # Optionally add the last few log messages to an 'Error Details' field
                error_details = "\n".join(logs[-5:]) # Get last 5 log messages
                table.update(airtable_record_id, {'Status': 'Error', 'Error Details': error_details})
                logs.append("Registro de Airtable actualizado a estado 'Error'.")
             except Exception as e:
                logs.append(f"Error al actualizar Airtable con estado de Error: {e}")


    return {"success": success, "content": analysis_markdown, "logs": logs}

# --- Airtable Update Function ---
def update_airtable_record(record_id, analysis_content):
    """Updates the Airtable record with the analysis."""
    try:
        table.update(record_id, {'Analisis': analysis_content, 'Status': 'Completado'})
        print(f"Airtable record {record_id} updated successfully.")
        return True
    except Exception as e:
        print(f"Error updating Airtable record {record_id}: {e}")
        return False

def create_airtable_record(empresa, pais, consideraciones):
    """Creates an initial Airtable record and returns its ID and an error message if applicable."""
    try:
        # Ensure table object is valid (it should be based on checks above)
        record = table.create({
            'Empresa': empresa,
            'Pais': pais,
            'Consideraciones': consideraciones,
            'Status': 'Procesando'
        })
        # Log success on the server
        print(f"Created Airtable record {record['id']}") 
        return record['id'], None # Return ID and None for error
    except Exception as e:
        # Log the detailed error on the server
        print(f"Error creating Airtable record: {e}") 
        error_message = f"Error de Airtable al crear registro: {e}"
        return None, error_message # Return None for ID and the error message

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

# Remove the direct Airtable update functions if all logic is within run_genspark_interaction
# Or keep them if they are used elsewhere (e.g., directly from Flask)
# For now, create_airtable_record is used by Flask, update logic is inside run_genspark_interaction
del update_airtable_record # Remove the standalone update function as it's handled within run_genspark_interaction
