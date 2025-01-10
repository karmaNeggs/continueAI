from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, session, after_this_request, g, flash
from functions import (
    load_handover,
    call_gpt_onboarding,
    generate_token,
    load_tokens_from_file,
    save_tokens_to_file,
    append_to_handover_chat_history,
    generate_dynamic_handover_chat_prompt,
    call_function_by_name,
    call_gpt_handover,
    generate_summary,
    finish_handover,
    get_base_path,
    load_config,
    save_config
)

from threading import Thread
import webview
from flask_session import Session

import os
import sys
from werkzeug.utils import secure_filename
import zipfile
import json
import logging
import requests
import base64
from dotenv import load_dotenv

# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO)

from flask import send_file
import shutil


BASE_PATH = get_base_path()

load_dotenv()  # Loads variables from .env into environment

# # Client IDs and redirect URI for connections
REDIRECT_URI= os.getenv('REDIRECT_URI', 'http://127.0.0.1:5000/oauth_callback')
SECRET_KEY=os.getenv('SECRET_KEY', 'your_flask_secret_key')


app = Flask(__name__, template_folder=os.path.join(BASE_PATH, 'templates'), static_folder=os.path.join(BASE_PATH, 'static'))

prompts_folder=os.path.join(BASE_PATH, 'prompts')
encrypted_folder=os.path.join(BASE_PATH, 'encrypted')
temp_folder=os.path.join(BASE_PATH, 'temp')
session_folder=os.path.join(BASE_PATH, 'session')

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(BASE_PATH, 'session')
app.config["SESSION_PERMANENT"] = False  # You can choose based on your requirement
app.config["SESSION_USE_SIGNER"] = True  # Secure the session ID by signing it
Session(app)

app.secret_key = SECRET_KEY  # Replace with a secure key


def run_flask():
    # Ensure required directories exist
    for directory in [temp_folder, encrypted_folder]:
        if not os.path.exists(directory):
            os.makedirs(directory)

    app.run(host='127.0.0.1', port=5000, threaded=True)

# Load the config when Flask app is created
try:
    initial_config = load_config()
    logging.info(f"Loading config at startup: {initial_config}")
    # Populate the session with the loaded config
    if initial_config:
        app.config.update(initial_config)  # Store the config in app.config

except Exception as e:
    logging.info(f"Loading config failed at startup {e}")
    print(e)


# Define the API class for JavaScript to interact with
class API:
    def close_app(self):

        print("Close button clicked. Exiting application.")

        try:
            with app.test_request_context():
                restart_session()  # Clean session before exit
        except Exception as error:
            app.logger.error("Error removing or closing downloaded file handle", exc_info=error)

        if webview.windows:
            webview.windows[0].destroy()  # Gracefully close the WebView window
        sys.exit()  # Terminate the application


########################################################### Routes start #################################################################


@app.route('/')
def home():
    # Populate session on first access, check if it's already populated
    if not getattr(g, 'session_populated', False):
        for key, value in app.config.items():
            if key in ['openai_api_key', 
                        'claude_api_key', 
                        'google_api_key', 
                        'slack_webhook', 
                        'creator_signature',
                        'org_file',
                        'org_url',
                        'org_data_filename']:
                session[key] = value
                
        g.session_populated = True
    return render_template('home.html')

@app.route('/help')
def help():
    return render_template('help.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'generate_requestor_token':
            requestor_token = generate_token()
            session['requestor_token'] = requestor_token
            return render_template('settings.html', requestor_token=requestor_token)
        elif action == 'save_settings':

            fields = ['openai_api_key', 
                'claude_api_key', 
                'google_api_key', 
                'slack_webhook', 
                'creator_signature']
        
            # Update session with non-empty values from form
            for field in fields:
                form_value = request.form.get(field)
                if form_value:
                    session[field] = form_value

            org_file = request.files.get('org_file')  # Access files with request.files
            org_url = request.form.get('org_url')  # URL input comes from request.form
            
            try:
                if org_file:
                    org_data = json.load(org_file)
                    session['org_data'] = org_data
                    session['org_data_filename'] = org_file.filename  # Note: use filename property of FileStorage
                elif org_url:
                    response = requests.get(org_url)
                    response.raise_for_status()  # This can throw requests.exceptions.HTTPError
                    org_data = response.json()
                    session['org_data'] = org_data
                    session['org_data_filename'] = org_url
                else:
                    error_message = "No org credentials were provided in this save."
                    logging.info(error_message)
                    return render_template('settings.html', error=error_message, requestor_token=session.get('requestor_token'))

                logging.info(dict(session))
                save_config(dict(session))

                return redirect(url_for('home'))

            except json.JSONDecodeError as e:
                error_message = f"Failed to decode JSON from the file: {str(e)}"
            except requests.exceptions.RequestException as e:
                error_message = f"HTTP request failed: {str(e)}"
            except Exception as e:
                error_message = f"An unexpected error occurred: {str(e)}"

            logging.error(error_message)
            return render_template('settings.html', error=error_message, requestor_token=session.get('requestor_token'))

    else:
        return render_template('settings.html', requestor_token=session.get('requestor_token'))

########################################################### Handover functions #################################################################


@app.route('/restart_handover', methods=['GET', 'POST'])
def restart_handover():
    """
    Dynamic handover chat assistant.
    """
    restart_session()
    return render_template('handover.html')


@app.route('/handover', methods=['GET', 'POST'])
def handover():
    """
    Dynamic handover chat assistant.
    """

    session_data = session.copy()

    if request.method == 'POST':
        data = request.get_json()
        user_input = data.get('query', '').strip()

        # Initialize or retrieve session variables
        session.setdefault('handover_data', {})
        session.setdefault('handover_chat_history', [])
        session.setdefault('current_step', 1)

        # Append user input to chat history
        append_to_handover_chat_history(session_data['handover_chat_history'], "user", user_input)

        # Determine role and generate a dynamic prompt
        role = session_data['handover_data'].get("role", "generic")
        creator_signature = session_data.get("creator_signature", "PolyRaccoon")
        step = session_data.get('current_step', 1)
        prompt = generate_dynamic_handover_chat_prompt(role, step, session_data['handover_data'], session_data['handover_chat_history'])

        # Call GPT for a response
        llm_api_key = session.get('openai_api_key')
        gpt_response = call_gpt_handover(prompt, user_input, llm_api_key)

        # logging.info(f"gpt_response{prompt}")

        # Process GPT's response or function call
        if 'function_call' in gpt_response:
            function_name = gpt_response['function_call']['name']
            function_args = gpt_response['function_call']['arguments']
            # Dynamically call the specified function
            function_result = call_function_by_name(function_name, function_args, session_data)
            logging.info(function_result)
            # response  =  parse_function_call_results(function_result) or "Function executed successfully."
            response = function_result or "Function executed successfully, Let's continue with your handover."

        else:
            response = gpt_response.get("content", "Let's continue with your handover.")

        # Append GPT's response to chat history
        append_to_handover_chat_history(session['handover_chat_history'], "assistant", response)

        # Persist updated session data back to the session
        for key, value in session_data.items():
            session[key] = value

        # logging.info(f"session{session}")
        return jsonify({"response": response})

    # Initialize a new session for GET requests
    # session.clear()
    session['handover_data'] = {}
    session['handover_chat_history'] = []
    session['current_step'] = 1
    return render_template('handover.html')



########################################################### Handover completion functions #################################################################


@app.route('/handover_complete', methods=['GET', 'POST'])
def handover_complete():

    uploaded_files = request.files.getlist('files')
    uploaded_links = request.form.getlist('links')   
    handover_data = session.get('handover_data')

    os.makedirs(temp_folder, exist_ok=True)

    # Append the file details to the 'files' list

    if 'uploaded_files' not in handover_data:
        handover_data['uploaded_files'] = []
    
    if 'uploaded_files' not in session:
        session['uploaded_files'] = []

    for file in uploaded_files:
        filename = secure_filename(file.filename)
        file_path = os.path.join(temp_folder, filename)
        file.save(file_path)  # Save file to disk instead of storing its content in the session

        # Only store reference to the file location in the session
        session['uploaded_files'].append({
            'filename': filename,
            'content': file_path
        })

        handover_data['uploaded_files'].append({
            'filename': filename,
            'content': "Document"
        })
        
    # Append the link details to the 'links' list
    if 'uploaded_links' not in handover_data:
        handover_data['uploaded_links'] = []

    if 'uploaded_links' not in session:
        session['uploaded_links'] = []

    for link in uploaded_links:
        linkname = link
        link_content = "Document"

        session['uploaded_links'].append({
            'linkname': linkname,
            'content': link_content
        })

        handover_data['uploaded_links'].append({
            'linkname': linkname,
            'content': link_content
        })

    session_data = session.copy()

    if request.method == 'POST':
        try:
            # Process the files and finalize the handover
            summarize_file_option = request.form.get('summarize_file_option', 'no')
            logging.info(f"summarize_file_option: {summarize_file_option}") 
            handover_token, encrypted_filename = finish_handover(session_data, summarize_file_option)

            logging.info(f"Handover complete.. handover_token: hidden, type: {type(handover_token)}")
            logging.info(f"Handover complete.. encrypted_filename: {encrypted_filename}, type: {type(encrypted_filename)}")

            # #Save the data in the session
            session['handover_token'] = str(handover_token)
            session['encrypted_filename'] = str(encrypted_filename)

            # Return a success response
            return render_template(
                'handover_complete.html',
                handover_token=handover_token,
                encrypted_filename=encrypted_filename,
                errors=errors
            )

        except Exception as e:
            # return render_template('handover.html', error=f"An error occurred: {str(e)}")
            # Handle errors gracefully
            return jsonify({'error': str(e)}), 500


    # For GET requests, render the handover complete page
    handover_token = session.get('handover_token', 'Empty handover :(')
    errors = session.get('errors', [])
    encrypted_filename = session.get('encrypted_filename', '')

    logging.info(f"handover closing for: {encrypted_filename}, handover_token: {handover_token}")
    
    return render_template(
        'handover_complete.html',
        handover_token=handover_token,
        encrypted_filename=encrypted_filename,
        errors=errors
    )



@app.route('/chat', methods=['POST'])
def handle_chat():

    data = request.get_json()
    user_input = data.get('query', '').strip()

    #re-using the handover chat hoistory function
    onboarding_chat_history = session.get('onboarding_chat_history', [])

    data = request.get_json()
    query = data.get('query')
    onboarding_data = session.get('onboarding_data')
    logging.info(onboarding_data)

    llm_api_key = session.get('openai_api_key')
    if not llm_api_key or not onboarding_data:
        return jsonify({"error": "API Key not set or handover data not loaded."}), 400
    response = call_gpt_onboarding(query, onboarding_data, onboarding_chat_history, llm_api_key)

    #intentionally re-using a function
    append_to_handover_chat_history(session['onboarding_chat_history'], "user", user_input)
    append_to_handover_chat_history(session['onboarding_chat_history'], "assistant", response)

    return jsonify({"response": response})



########################################################### Onboarding functions #################################################################
@app.route('/restart_onboarding', methods=['POST'])
def restart_onboarding():

    # restart_session("onboarding")
    session['onboarding_chat_history'] = [] # Clear chat history
    return jsonify({'success': True})  # Respond with JSON


@app.route('/onboarding', methods=['GET', 'POST'])
def onboarding():
    if request.method == 'POST':
        # Check if any files are uploaded
        action = request.form.get('action')
        if action == 'upload':
            if 'handover_files' not in request.files:
                app.logger.error("No files found in the request.")
                return "Error: No files uploaded", 400

            files = request.files.getlist('handover_files')
            tokens = [request.form.get(f'token_{i}') for i in range(len(files))]

            if not files or not all(tokens):
                app.logger.error("Files or tokens are missing.")
                return "Error: Missing files or tokens", 400

            all_handover_data = []
            extracted_files = []
            session.setdefault('onboarding_chat_history', [])

            llm_api_key = session.get('openai_api_key')

            try:
                for file, token in zip(files, tokens):
                    # Load and unpack each file
                    handover_data, file_list = load_handover(file, token)
                    all_handover_data.append(handover_data)
                    extracted_files.extend(file_list)

                # Store the combined handover data in the session
                session['onboarding_data'] = all_handover_data
                session['extracted_files'] = extracted_files

                # Render the onboarding template with all data and extracted files
                flash('Files uploaded successfully.')  # Optional: Flash a success message

                return render_template('onboarding.html', extracted_files=extracted_files)

            except Exception as e:
                error_message = str(e)
                app.logger.error(f"Error processing files: {error_message}")
                return render_template('onboarding.html', error="Check Configuration Settings")

        elif action == 'summarize-onboarding':
            # Handle summarization
            onboarding_data = session.get('onboarding_data', [])
            extracted_files = session.get('extracted_files', [])
            llm_api_key = session.get('openai_api_key')

            if onboarding_data:
                prompt_path = os.path.join(prompts_folder, 'Onboarding_summary_prompt.txt')
                onboarding_summary = generate_summary(prompt_path, json.dumps(onboarding_data), llm_api_key)
                
                flash('Summarization completed.')  # Optional: Flash a success message
                session['onboarding_summary'] = onboarding_summary
                
                return jsonify({'onboarding_summary': onboarding_summary})

            return jsonify({'error': 'No data to summarize'})

    return render_template('onboarding.html')


@app.route('/download_extracted_file/<filename>')
def download_extracted_file(filename):
    return send_from_directory(directory='temp', path=filename, as_attachment=True)


def restart_session(session_type = "handover"):
    """
    Restarts the handover session by clearing existing handover-related session data.
    """
    # List of handover-related fields to clear/reset
    fields_to_clear = [
        'onboarding_chat_history'
    ] if session_type == "onboarding" else [
        'handover_data',
        'uploaded_files',
        'uploaded_links',
        'current_step',
        'handover_chat_history',
        'handover_token',
        'encrypted_filename',
        'onboarding_data',
        'extracted_files',
        'onboarding_summary',
        'onboarding_chat_history'
    ]

    for field in fields_to_clear:
        # Remove the field if it exists
        session.pop(field, None)

    return {"message": "Chat session has been restarted."}



########################################################### Route to start Summary #################################################################






########################################################### Route to upload sharing file  #################################################################


@app.route('/download_handover', methods=['GET'])
def download_handover():
    custom_filename = request.args.get('filename')
    
    # Ensure filename is provided and has the correct extension
    if not custom_filename:
        return render_template('handover_complete.html', error="Please provide a valid filename.")
    
    # Append .hrcx extension if not already present
    if not custom_filename.endswith('.hrcx'):
        custom_filename += '.hrcx'

    # Check if the original file (handover.hrcx) exists
    original_filename = 'handover.hrcx'

    # Check if the file exists
    
    file_path = os.path.join(encrypted_folder, original_filename)

    logging.info(f"package file path {file_path}.")

    if not os.path.isfile(file_path):
        return render_template('handover_complete.html', error="File not found. Please ensure the handover file was created successfully.")

    # Serve the file for download with the custom filename shown to the user
    response = send_from_directory(
        directory= encrypted_folder,
        path=original_filename,
        as_attachment=True,
        download_name=custom_filename
    )
    response.headers["Content-Disposition"] = f"attachment; filename={custom_filename}"
    return response



@app.route('/upload_file_to_fileio', methods=['POST'])
def upload_file_to_fileio():
    try:
        data = request.get_json()
        logging.info(data)
        custom_filename = data.get('filename', 'handover.hrcx')

        # Ensure filename has the correct extension
        if not custom_filename.endswith('.hrcx'):
            custom_filename += '.hrcx'

        file_path = os.path.join(encrypted_folder, 'handover.hrcx')  # Source file path

        logging.info(f"package file must be present at {file_path}.")

        if not os.path.isfile(file_path):
            raise Exception("File not found.")

        expires = '1d'
        url = f"https://file.io/?expires={expires}"

        with open(file_path, 'rb') as f:
            files = {'file': (custom_filename, f, 'application/octet-stream')}
            response = requests.post(url, files=files)
        
        response.raise_for_status()
        data = response.json()

        if data.get('success'):
            shareable_link = data['link']  # The shareable file link
        else:
            raise Exception("Failed to upload file to file.io")

        return jsonify(success=True, link=shareable_link)

    except Exception as e:
        app.logger.error(f"Error uploading to FileIO: {e}")
        return jsonify(success=False, error="Error uploading file to FileIO.")


@app.route('/upload_to_transfersh', methods=['POST'])
def upload_to_transfersh():
    try:
        data = request.get_json()
        custom_filename = data.get('filename', 'handover.hrcx')

        # Ensure filename has the correct extension
        if not custom_filename.endswith('.hrcx'):
            custom_filename += '.hrcx'

        file_path = os.path.join(encrypted_folder, 'handover.hrcx')  # Source file path
        if not os.path.isfile(file_path):
            raise Exception("File not found.")

        with open(file_path, 'rb') as f:
            response = requests.post(f'https://transfer.sh/{custom_filename}', files={'file': f}, timeout=30)
        
        if response.status_code == 200:
            shareable_link = response.text.strip()
            return jsonify(success=True, link=shareable_link)
        else:
            raise Exception(f"Failed to upload file to Transfer.sh. Status: {response.status_code}")

    except Exception as e:
        app.logger.error(f"Error uploading to Transfersh: {e}")
        return jsonify(success=False, error="Error uploading file to transfer.sh")



@app.route('/share_to_slack', methods=['POST'])
def share_to_slack():

    session.get('openai_api_key')
    try:
        data = request.get_json()
        link = data.get('link')

        if not link:
            return jsonify(success=False, error="No link provided"), 400

        payload = {
            'text': f"Talk to my handover's memory: {link}"
        }
        response = requests.post(session.get('slack_webhook'), json=payload)
        if response.status_code == 200:
            return jsonify(success=True, message="Link shared successfully to Slack!")
        else:
            return jsonify(success=False, error=f"Failed to share link to Slack. Status code: {response.status_code}")
    except Exception as e:
        return jsonify(success=False, error=f"An error occurred: {str(e)}")



if __name__ == '__main__':
    # Start Flask app in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    api = API()

    # Launch the webview with non-resizable settings
        # Create a PyWebView window without unsupported arguments
    window = webview.create_window(
        title="Continue",
        url="http://127.0.0.1:5000/",
        width=1200,
        height=800,
        resizable=False,
        fullscreen=False,
        confirm_close=True,
        easy_drag=False,
        text_select=True,
        frameless=True,
        js_api=api
        # Removed minimizable and maximizable
    )

    webview.settings = {
        'ALLOW_DOWNLOADS': True, # Allow file downloads
        'ALLOW_FILE_URLS': True, # Allow access to file:// urls
        'OPEN_EXTERNAL_LINKS_IN_BROWSER': True, # Open target=_blank links in an external browser
        'OPEN_DEVTOOLS_IN_DEBUG': True, # Automatically open devtools when `start(debug=True)`.
    }

    webview.start()











#     @app.route('/upload_to_dropbox', methods=['POST'])
# def upload_to_dropbox():
#     tokens = load_tokens_from_file('dropbox')
#     access_token = tokens.get('access_token')

#     if not access_token:
#         return jsonify(success=False, error="User not authorized for Dropbox.")

#     filename = request.json['filename']
#     file_path = os.path.join('encrypted', filename)

#     with open(file_path, 'rb') as f:
#         headers = {
#             'Authorization': f'Bearer {access_token}',
#             'Dropbox-API-Arg': '{"path": "/' + filename + '", "mode": "add", "autorename": true}',
#             'Content-Type': 'application/octet-stream'
#         }
#         response = requests.post('https://content.dropboxapi.com/2/files/upload', headers=headers, data=f)

#     if response.status_code == 401:  # Unauthorized due to expired token
#         print("Dropbox access token expired. Attempting to refresh.")
#         new_access_token = refresh_token('dropbox')
#         if new_access_token:
#             headers['Authorization'] = f'Bearer {new_access_token}'
#             with open(file_path, 'rb') as f:
#                 response = requests.post('https://content.dropboxapi.com/2/files/upload', headers=headers, data=f)

#     if response.status_code == 200:
#         try:
#             link_response = requests.post(
#                 'https://api.dropboxapi.com/2/sharing/create_shared_link_with_settings',
#                 headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
#                 json={"path": f"/{filename}", "settings": {"requested_visibility": "public"}}
#             )
#             link_response.raise_for_status()  # Ensure it raises HTTPError for bad status
#             shareable_link = link_response.json().get('url')
#             return jsonify(success=True, link=shareable_link)
#         except requests.exceptions.HTTPError as e:
#             print("HTTP error during link generation:", e)
#             print("Dropbox link generation error:", link_response.text)  # Log response text for non-JSON
#             return jsonify(success=False, error="Error generating Dropbox link.")
#         except requests.exceptions.JSONDecodeError:
#             print("Dropbox link generation response not in JSON format")
#             print("Response text:", link_response.text)  # Log non-JSON response text
#             return jsonify(success=False, error="Unexpected response format from Dropbox.")
#     else:
#         try:
#             print("Dropbox upload error:", response.json())
#         except requests.exceptions.JSONDecodeError:
#             print("Dropbox upload error: Response not in JSON format")
#             print("Response text:", response.text)  # Log raw response text
#         return jsonify(success=False, error="Error uploading file to Dropbox.")



# @app.route('/download_all', methods=['GET'])
# def download_all():
#     handover_data = session.get('handover_data')
#     if not handover_data:
#         return "Handover data not available.", 400

#     # Create a ZIP file containing all the handover data
#     temp_zip = 'all_files.zip'
#     with zipfile.ZipFile(temp_zip, 'w') as zipf:
#         for filename, data in handover_data.items():
#             # Write individual JSON files for each handover
#             json_filename = f'{filename}_handover.json'
#             zipf.writestr(json_filename, json.dumps(data))

#         # Add other files if needed (ensure the files exist)
#         for extracted_file in os.listdir('temp'):
#             zipf.write(os.path.join('temp', extracted_file), extracted_file)

#     @after_this_request
#     def remove_file(response):
#         try:
#             os.remove(temp_zip)
#         except Exception as error:
#             app.logger.error("Error removing or closing downloaded file handle", exc_info=error)
#         return response

#     return send_from_directory(directory='.', path=temp_zip, as_attachment=True)

# @app.route('/summarize_files', methods=['POST'])
# def summarize_files():
#     summaries = []
#     errors = []
#     resources = session.get('uploaded_files', {})
#     llm_api_key = session.get('openai_api_key')

#     if resources and llm_api_key:
#         try:
#             file_summaries, file_errors = summarize_offline_files(resources, llm_api_key)
#             summaries.extend(file_summaries)
#             errors.extend(file_errors)
#         except Exception as e:
#             error_message = f"Error processing offline files: {e}"
#             logging.error(error_message)
#             errors.append(error_message)
    
#     if 'summaries' not in session:
#         session['summaries'] = []
#     session['summaries'].extend(summaries)

#     if errors:
#         return jsonify({'success': False, 'message': 'Errors occurred while summarizing files.', 'errors': errors}), 500
#     else:
#         return jsonify({'success': True, 'message': 'Summaries successfully generated.'})
