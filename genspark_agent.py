# filename: genspark_agent.py
import asyncio
import os
import traceback
from playwright.async_api import async_playwright, TimeoutError
from dotenv import load_dotenv
from pyairtable import Api  # <-- Import Airtable API

# --- Load Environment Variables ---
load_dotenv() # Load variables from .env file

# Genspark Credentials
email = os.getenv("GENSPARK_EMAIL")
password = os.getenv("GENSPARK_PASSWORD")

# Airtable Credentials
airtable_api_key = os.getenv("AIRTABLE_API_KEY")
airtable_base_id = os.getenv("AIRTABLE_BASE_ID")

# Check if all credentials were loaded
if not email or not password or not airtable_api_key or not airtable_base_id:
    print("Error Critico: No se encontraron todas las credenciales necesarias.")
    print("Asegurate de que tu archivo '.env' contenga:")
    print("GENSPARK_EMAIL=\"tu_email@ejemplo.com\"")
    print("GENSPARK_PASSWORD=\"tu_contraseña\"")
    print("AIRTABLE_API_KEY=\"keyXXXXXXXXXXXXXX\"") # Example format
    print("AIRTABLE_BASE_ID=\"appXXXXXXXXXXXXXX\"") # Example format
    exit(1) # Exit the script if credentials are missing

async def run_genspark_interaction(loaded_email, loaded_password):
    # Define the long query
    long_query = """Realiza un análisis de la empresa [EMPRESA] que radica en [PAIS]. Debes tener las siguientes consideraciones: [CONSIDERACIONES]. 
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

    final_result = "Script did not complete." # Default result

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Increase default timeout for long waits (e.g., 15 minutes)
        page.set_default_timeout(900000) # 15 minutes in milliseconds

        try:
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

            # --- Second Login Sequence (as requested) ---
            print("\n--- Starting Second Login Sequence ---")
            try:
                print("[Step 14] Looking for 'Login with email' button again...")
                await page.locator(login_email_button_selector).first.click()
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

            except Exception as e:
                print(f"Error during second login attempt (maybe already logged in?): {e}")
                print("Attempting to continue assuming login state is correct...")

            print("[Step 21] Waiting 2 seconds after second sign in attempt...")
            await asyncio.sleep(2)
            print("Current URL after second login attempt:", page.url)

            # --- Main Task Sequence ---
            print("\n--- Starting Main Task Sequence ---")

            print("[Step 22/23] Looking for and clicking 'Investigación Profunda'...")
            investigacion_selector = 'div.title:has-text("Investigación Profunda")'
            try:
                await page.wait_for_selector(investigacion_selector, timeout=20000)
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

            # --- MODIFIED: Wait indefinitely (up to page timeout) for specific image response ---
            print("[NEW Step 26a] Waiting for specific image network response (up to 15 minutes)...")
            try:
                # Wait for the next response event that matches the criteria
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
                # Stop the script if the crucial signal is not received
                raise Exception("Timeout waiting for the specific image response signal.")
            # --- END: Wait for specific image response ---

            # Step 27/28: Find and click second-to-last ".buttons" element (Renumbered from 28/29)
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
            clipboard_content = "" # Initialize clipboard content
            raw_clipboard_content = "" # Store the raw content before processing
            try:
                await context.grant_permissions(['clipboard-read', 'clipboard-write'])
                raw_clipboard_content = await page.evaluate('navigator.clipboard.readText()')
                print("Successfully read clipboard.")

                # --- NEW: Process clipboard content --- 
                print("Processing clipboard content to find first '#'...")
                try:
                    first_hash_index = raw_clipboard_content.index('#')
                    clipboard_content = raw_clipboard_content[first_hash_index:].strip()
                    print("Content processed. Starting from first '#'.")
                except ValueError:
                    # Handle case where '#' is not found
                    print("Warning: '#' not found in clipboard content. Using original content for Airtable.")
                    clipboard_content = raw_clipboard_content.strip() 
                # --- END: Process clipboard content ---

            except Exception as e:
                print(f"Error reading clipboard: {e}")
                print("Clipboard access might be denied by browser security settings.")
                clipboard_content = f"Error reading clipboard: {e}"
                # raw_clipboard_content remains empty or holds partial data if evaluate failed mid-way


            # Step 30: Send to Airtable
            print("[Step 30] Attempting to send data to Airtable...")
            # Use the (potentially processed) clipboard_content
            if clipboard_content:
                try:
                    api = Api(airtable_api_key)
                    # Specify your table name and column name exactly
                    table = api.table(airtable_base_id, 'AnalisisInicial')
                    record_data = {
                        'Analisis': clipboard_content.strip() # The column name must match Airtable
                    }
                    response = table.create(record_data)
                    print(f"Successfully created Airtable record: ID {response['id']}")
                    final_result = f"Airtable record created: {response['id']}"
                except Exception as e:
                    print(f"Error sending data to Airtable: {e}")
                    final_result = f"Error sending to Airtable: {e}. Clipboard content was: \n{clipboard_content.strip()}"
            else:
                print("Skipping Airtable: No content retrieved from clipboard.")
                final_result = "Airtable skipped: No clipboard content."

        except TimeoutError as e:
            print(f"A timeout occurred during the process: {e}")
            final_result = f"Operation timed out: {e}"
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            print(traceback.format_exc())
            final_result = f"An unexpected error occurred: {e}"
        finally:
            print("\nClosing browser...")
            await browser.close()

        return final_result

async def main():
    print("Starting Genspark agent with complex workflow (using .env)...")
    response = await run_genspark_interaction(email, password)

    # Modified final output message
    print(f"\n--- Script Finished ---")
    print(f"Final Status: {response}")
    print("-----------------------")

if __name__ == "__main__":
    if email and password and airtable_api_key and airtable_base_id:
        asyncio.run(main())
    else:
        pass # Error message already printed at the top 