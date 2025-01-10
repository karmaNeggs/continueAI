let shareableLink = '';

document.addEventListener('DOMContentLoaded', function() {
    // Handle dynamic form changes based on role selection or steps

    const originalChatForm = document.getElementById('chat-form');
    if (originalChatForm) {
        originalChatForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const query = document.getElementById('chat-input').value;
            fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            })
                .then(response => response.json())
                .then(data => {
                    const chatBox = document.getElementById('chat-box');
                    if (data.response) {
                        chatBox.innerHTML += `<div class="user-message">${query}</div>`;
                        chatBox.innerHTML += `<div class="bot-response">${data.response}</div>`;
                        chatBox.scrollTop = chatBox.scrollHeight;
                        document.getElementById('chat-input').value = '';
                    } else if (data.error) {
                        chatBox.innerHTML += `<div class="bot-response">Error: ${data.error}</div>`;
                    }
                })
                .catch(error => {
                    console.error('Error during chat:', error);
                });
        });
    }

    // Restart onboarding button
    const restartButton = document.getElementById('restart-onboarding-button');
    if (restartButton) {
        restartButton.addEventListener('click', function(e) {
            e.preventDefault(); // Prevents the page from reloading
            fetch('/restart_onboarding', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const chatBox = document.getElementById('chat-box');
                    chatBox.innerHTML = ''; // Clear chat box content
                    alert('Onboarding has been restarted successfully.');
                }
            })
            .catch(error => {
                console.error('Error restarting onboarding:', error);
                alert('Failed to restart. Please try again.');
            });
        });
    }

    // Summarize onboarding button
    const summarizeButton = document.getElementById('summarize-button');
    if (summarizeButton) {
        summarizeButton.addEventListener('click', function(e) {
            e.preventDefault(); // Prevents the page from reloading
            fetch('/onboarding', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ action: 'summarize-onboarding' })
            })
            .then(response => response.json())
            .then(data => {
                if (data.onboarding_summary) {
                    const summaryContainer = document.querySelector('.project-report-container-o');
                    summaryContainer.innerHTML = `<h3 class="gradient-text">Summary of Handovers</h3>
                                                    <pre class="project-report-content">${data.onboarding_summary}</pre>`;
                } else if (data.error) {
                    alert(`Error: ${data.error}`);
                }
            })
            .catch(error => {
                console.error('Error summarizing onboarding:', error);
                alert('Failed to summarize. Please try again.');
            });
        });
    }
    

    // Handle the new handover chatbot functionality
    const handoverChatForm = document.getElementById('handover-chat-form');
    if (handoverChatForm) {
    handoverChatForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const query = document.getElementById('handover-chat-input').value;
        fetch('/handover', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        })
            .then(response => response.json())
            .then(data => {
                const chatBox = document.getElementById('handover-chat-box');
                if (data.response) {
                    chatBox.innerHTML += `<div class="user-message">${query}</div>`;
                    chatBox.innerHTML += `<div class="bot-response">${data.response}</div>`;
                    chatBox.scrollTop = chatBox.scrollHeight;
                    document.getElementById('handover-chat-input').value = '';
                } else if (data.error) {
                    chatBox.innerHTML += `<div class="bot-response">Error: ${data.error}</div>`;
                }
            })
            .catch(error => {
                console.error('Error during handover chat:', error);
            });
    });
    }


    // Handover restart button

    const restartHandoverButton = document.getElementById('restart-handover-button');

    if (restartHandoverButton) {
        restartHandoverButton.addEventListener('click', function () {
            fetch('/restart_handover', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'handover_complete' })
            })
                .then(response => {
                    if (response.ok) {
                        window.location.href = '/handover';
                    } else {
                        alert('Failed to complete handover. Please try again.');
                    }
                })
                .catch(error => {
                    console.error('Error completing handover:', error);
                    alert('An error occurred. Please try again.');
                });
        });
    }

    // Handle custom handover complete
    const completeHandoverButton = document.getElementById('complete-handover-button');

    if (completeHandoverButton) {
        completeHandoverButton.addEventListener('click', function () {
            // Create FormData object
            const formData = new FormData();

            // Append each file from uploadedFiles to the FormData
            uploadedFiles.forEach((file) => {
                formData.append('files', file);
            });

            // Append each link from uploadedLinks to the FormData
            uploadedLinks.forEach((link) => {
                formData.append('links', link);
            });

            // Append the summarize file option (from the checkbox)
            const summarizeFilesCheckbox = document.getElementById('summarize-files-checkbox');
            if (summarizeFilesCheckbox && summarizeFilesCheckbox.checked) {
                formData.append('summarize_file_option', 'yes');
            } else {
                formData.append('summarize_file_option', 'no');
            }

            // Send the request with FormData
            fetch('/handover_complete', {
                method: 'POST',
                body: formData
            })
                .then(response => response.json()) // Parse the JSON response
                .then(data => {
                    console.log('Response from server:', data);
                    // Use data.handover_token, data.encrypted_filename, etc., as needed
                    window.location.href = '/handover_complete';
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred. Please try again.');
                });
        });
    }



    // // Handle file uploads for the new handover functionality

    const handoverDropZone = document.getElementById('handover-drop-zone');
    const handoverFileInput = document.getElementById('handover-upload-files');
    const handoverFileList = document.getElementById('handover-file-list');
    const handoverLinkInput = document.getElementById('handover-link-input');

    
    let uploadedFiles = [];
    let uploadedLinks = [];
    const MAX_TOTAL_SIZE = 66.6 * 1024 * 1024; // Convert MB to Bytes
    
    if (handoverDropZone && handoverFileInput) {
        // Drag-and-drop functionality
        handoverDropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            handoverDropZone.classList.add('dragging');
        });
    
        handoverDropZone.addEventListener('dragleave', () => {
            handoverDropZone.classList.remove('dragging');
        });
    
        handoverDropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            handoverDropZone.classList.remove('dragging');
    
            const droppedData = e.dataTransfer.getData('text/plain');
            if (droppedData && isValidURL(droppedData)) {
                handleHandoverLinks(droppedData);
            } else {
                handleHandoverFiles(e.dataTransfer.files);
            }
        });
    
        // Toggle between inputs on click
        handoverDropZone.addEventListener('click', () => toggleInputSections(handoverLinkInput, handoverFileInput));
    }    

    // Handover flow file input handling
    if (handoverFileInput) {
        handoverFileInput.addEventListener('change', (e) => handleHandoverFiles(e.target.files));
    }
    
    // URL input handling
    if (handoverLinkInput) {
        handoverLinkInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const url = e.target.value.trim();
                if (url && isValidURL(url)) {
                    handleHandoverLinks(url);
                    e.target.value = ''; // Clear input
                    toggleInputSections(handoverLinkInput, handoverFileInput); // Toggle back to drop zone
                } else {
                    alert('Invalid URL');
                }
            }
        });

    }

    
    function handleHandoverFiles(files) {
        let totalSize = uploadedFiles.reduce((sum, file) => sum + file.size, 0);
    
        for (const file of files) {
            if (isSupportedFileType(file.name)) {
                if (uploadedFiles.some((f) => f.name === file.name)) {
                    alert(`File "${file.name}" is already uploaded.`);
                    continue;
                }
    
                if (totalSize + file.size > MAX_TOTAL_SIZE) {
                    alert(`Adding "${file.name}" exceeds the maximum total size of 66.6 MB.`);
                    continue;
                }
    
                uploadedFiles.push(file);
                totalSize += file.size;
    
                // Add file to the list
                const listItem = document.createElement('li');
                listItem.textContent = `📄 ${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
    
                const removeButton = createRemoveButton(() => {
                    uploadedFiles = uploadedFiles.filter((f) => f !== file);
                    listItem.remove();
                });
    
                listItem.appendChild(removeButton);
                handoverFileList.appendChild(listItem);
            } else {
                alert(`Unsupported file type: "${file.name}"`);
            }
        }
    }
    
    function handleHandoverLinks(link) {
        if (uploadedLinks.includes(link)) {
            alert(`Link "${link}" is already added.`);
            return;
        }
    
        uploadedLinks.push(link);
    
        const listItem = document.createElement('li');
        listItem.textContent = `🔗 ${link}`;
    
        const removeButton = createRemoveButton(() => {
            uploadedLinks = uploadedLinks.filter((l) => l !== link);
            listItem.remove();
        });
    
        listItem.appendChild(removeButton);
        handoverFileList.appendChild(listItem);
    }
    

    function toggleInputSections(url, file) {
        if (!url.hidden) { // If URL input is visible
            if (url !== document.activeElement) { // If URL input is not focused
                file.click(); // Trigger file input click
                url.hidden = true; // Hide the URL input
            }
        } else { // If URL input is hidden
            file.click(); // Trigger file input click
            url.hidden = false; // Show the URL input
        }
    }
    

    
    // Utility to create remove buttons
    function createRemoveButton(onClick) {
        const removeButton = document.createElement('img');
        removeButton.src = 'static/remove.png'; // Path to your static image
        removeButton.alt = 'Remove';
        removeButton.style.marginLeft = '10px';
        removeButton.style.cursor = 'pointer';
        removeButton.style.width = '20px';
        removeButton.style.height = '20px';
        removeButton.addEventListener('click', onClick);
        return removeButton;
    }
    
    // Validate URL
    function isValidURL(url) {
        try {
            new URL(url); // Parse to validate
            return true;
        } catch {
            return false;
        }
    }
    
    // Validate supported file types
    function isSupportedFileType(fileName) {
        const allowedExtensions = ['.txt', 'csv', 'xlxb', '.pdf', '.ppt', '.pptx', '.xls', '.xlsx', '.doc', '.docx','.mp3','.wav','.jpg','.jpeg','.svg','.png','hrcx'];
        return allowedExtensions.some((ext) => fileName.toLowerCase().endsWith(ext));
    }



    // // Handle file uploads for the new settings functionality
    // Settings URL input handling 
    const authDropZone = document.getElementById('auth-drop-zone');
    const orgFileInput = document.getElementById('org_file');
    const orgUrlInput = document.getElementById('org_url');
    
    // Drag-and-drop functionality
    if (authDropZone && orgFileInput) {
        authDropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            authDropZone.classList.add('dragging');
        });
    
        authDropZone.addEventListener('dragleave', () => {
            authDropZone.classList.remove('dragging');
        });
    
        authDropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            authDropZone.classList.remove('dragging');
    
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                orgFileInput.files = files; // Attach the dropped file to the file input
                orgFileInput.style.display = 'block';
                orgUrlInput.style.display = 'none';
            } else {
                const droppedData = e.dataTransfer.getData('text/plain');
                if (droppedData && isValidURL(droppedData)) {
                    orgUrlInput.value = droppedData; // Populate the URL input
                    orgUrlInput.style.display = 'block';
                    orgFileInput.style.display = 'none';
                } else {
                    alert('Invalid URL or file.');
                }
            }
        });
    
        // Click event to toggle inputs
        authDropZone.addEventListener('click', () => toggleInputSections(orgUrlInput, orgFileInput));
    }
    
    // Settings URL input handling
    if (orgUrlInput) {
        orgUrlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const url = e.target.value.trim();
                if (url && isValidURL(url)) {
                    orgUrlInput.style.display = 'block';
                    orgFileInput.style.display = 'none';
                } else {
                    alert('Invalid URL');
                }
            }
        });
    }
    

    // Handle dynamic token input display based on file input
    const fileInput = document.getElementById('handover_files');
    const tokenInputsContainer = document.getElementById('token-inputs');
    const loadButton = document.getElementById('load-button');

    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const files = fileInput.files;
            tokenInputsContainer.innerHTML = ''; // Clear existing token inputs

            if (files.length > 0) {
                for (let i = 0; i < files.length; i++) {
                    const tokenInput = document.createElement('input');
                    tokenInput.type = 'text';
                    tokenInput.name = `token_${i}`;
                    tokenInput.placeholder = `Enter token for ${files[i].name}`;
                    tokenInput.required = true;
                    tokenInputsContainer.appendChild(tokenInput);
                }
                tokenInputsContainer.style.display = 'block';
                loadButton.disabled = false;
            } else {
                tokenInputsContainer.style.display = 'none';
                loadButton.disabled = true;
            }
        });
    }

    // // Listen for the postMessage event from the new tab/window
    // window.addEventListener("message", function(event) {
    //     if (event.data === "authSuccess") {
    //         alert("Authorization successful! You can proceed with your task.");
    //         // Retry the upload process automatically if needed
    //         // document.getElementById('upload-google-drive').click();
    //     }
    // }, false);

//#####################################  Sharing Handover upload links ######################################


    // Function for FileIo upload
    window.uploadToFileio = function() {

        const filename = document.getElementById('filename').value;
        if (!filename) {
            alert("Please provide a filename");
            return;
        }

        fetch('/upload_file_to_fileio', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filename: filename })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('File uploaded to FileIO successfully. Shareable link generated.');
                displayShareableLink(data.link);
            } else {
                alert('Error uploading file to FileIO: ' + data.error);
            }
        });
    };


    // Function for transfersh upload
    window.uploadToTransfersh = function() {

        const filename = document.getElementById('filename').value;
        if (!filename) {
            alert("Please provide a filename");
            return;
        }

        fetch('/upload_to_transfersh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filename: filename })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('File uploaded to transfersh successfully. Shareable link generated.');
                displayShareableLink(data.link);
            } else {
                alert('Error uploading file to transfersh: ' + data.error);
            }
        });
    };
    

    // Function to display the shareable link and reveal the additional icons
    function displayShareableLink(link) {
        console.log("Link to display:", link);
        const linkContainer = document.getElementById('shareable-link-container');
        const linkElement = document.getElementById('shareable-link');
        const additionalIcons = document.getElementById('additional-icons');

        if (link) {
            shareableLink = link;
            linkElement.textContent = link;
            linkContainer.style.display = 'block';
            additionalIcons.style.display = 'flex';
            console.log("Link displayed and additional icons shown.");
        } else {
            console.error("No link provided.");
        }
    }

//#####################################  Sharing Handover links ######################################

    // Function to toggle the visibility of error messages
    window.toggleErrorMessage = function (id) {
        const errorDiv = document.getElementById(id);
        if (errorDiv.style.display === "none") {
            errorDiv.style.display = "block";
        } else {
            errorDiv.style.display = "none";
        }
    };

    // Function to share the link to Slack via Flask backend
    window.shareToSlack = function() {
        if (shareableLink) {
            fetch('/share_to_slack', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ link: shareableLink })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('✅ Link shared successfully to Slack!');
                } else {
                    alert(`❌ Failed to share link to Slack: ${data.error}`);
                }
            })
            .catch(error => {
                alert(`❌ An error occurred: ${error.message}`);
            });
        } else {
            alert('No link available to share. Please generate a link first.');
        }
    };


    // Function to share the generated link via mail
    // window.shareToMail = function() {
    //     if (shareableLink) {
    //         const subject = "Your Handover Package";
    //         const body = `Talk to my handover's memory: ${shareableLink}`;
    //         window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    //     } else {
    //         alert('No link available to share. Please generate a link first.');
    //     }
    // };

    // // Function to share the link via WhatsApp Web
    // window.shareToWhatsApp = function() {
    //     if (shareableLink) {
    //         const message = `Talk to my handover's memory: ${shareableLink}`;
    //         window.open(`https://web.whatsapp.com/send?text=${encodeURIComponent(message)}`);
    //     } else {
    //         alert('No link available to share. Please generate a link first.');
    //     }
    // };
});







    // // Function to initiate Google Drive upload or authorization
    // window.uploadToGoogleDrive = function() {

    //     const filename = document.getElementById('filename').value;
    //     if (!filename) {
    //         alert("Please provide a filename");
    //         return;
    //     }

    //     console.log('Starting check for Google Drive authorization...');

    //     fetch('/check_google_auth', {
    //         method: 'GET'
    //     })
    //     .then(response => {
    //         console.log('Response from /check_google_auth:', response);
    //         return response.json();
    //     })
    //     .then(data => {
    //         console.log('Data received from /check_google_auth:', data);

    //         if (data.authorized) {
    //             console.log('User is authorized for Google Drive. Proceeding with upload...');

    //             // Proceed with uploading the file
    //             fetch('/upload_to_google_drive', {
    //                 method: 'POST',
    //                 headers: {
    //                     'Content-Type': 'application/json'
    //                 },
    //                 body: JSON.stringify({ filename: 'handover.hrcx' })
    //             })
    //             .then(response => {
    //                 console.log('Response from /upload_to_google_drive:', response);
    //                 return response.json();
    //             })
    //             .then(data => {
    //                 console.log('Data received from /upload_to_google_drive:', data);

    //                 if (data.success) {
    //                     alert('File uploaded to Google Drive successfully. Shareable link generated.');
    //                     displayShareableLink(data.link);
    //                 } else {
    //                     console.error('Error uploading file to Google Drive:', data.error);
    //                     alert('Error uploading file to Google Drive: ' + data.error);
    //                 }
    //             })
    //             .catch(uploadError => {
    //                 console.error('Error during upload request:', uploadError);
    //             });
    //         } else {
    //             console.warn('User not authorized for Google Drive. Redirecting to authorization page.');
    //             // Redirect to the authorization page
    //             window.open('/google_auth', '_blank');
    //             alert('Please authorize the app in the newly opened window/tab and then retry.');
    //         }
    //     })
    //     .catch(authCheckError => {
    //         console.error('Error during authorization check:', authCheckError);
    //     });
    // };



        // Function to initiate Dropbox upload or authorization
    // window.uploadToDropbox = function() {
    //     fetch('/check_dropbox_auth', {
    //         method: 'GET'
    //     })
    //     .then(response => response.json())
    //     .then(data => {
    //         if (data.authorized) {
    //             // Proceed with uploading the file
    //             fetch('/upload_to_dropbox', {
    //                 method: 'POST',
    //                 headers: {
    //                     'Content-Type': 'application/json'
    //                 },
    //                 body: JSON.stringify({ filename: 'handover.hrcx' })
    //             })
    //             .then(response => response.json())
    //             .then(data => {
    //                 if (data.success) {
    //                     alert('File uploaded to Dropbox successfully. Shareable link generated.');
    //                     displayShareableLink(data.link);
    //                 } else {
    //                     alert('Error uploading file to Dropbox: ' + data.error);
    //                 }
    //             });
    //         } else {
    //             // Redirect to the authorization page
    //             window.open('/dropbox_auth', '_blank');
    //             alert('Please authorize the app in the newly opened window/tab and then retry.');
    //         }
    //     });
    // };