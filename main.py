from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from PIL import Image
import io
import os
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")

app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica tus dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Transcriptor Paleográfico</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 800px;
                width: 100%;
            }
            h1 {
                color: #333;
                margin-bottom: 10px;
                font-size: 2em;
                text-align: center;
            }
            .subtitle {
                color: #666;
                text-align: center;
                margin-bottom: 30px;
                font-size: 0.95em;
            }
            .upload-area {
                border: 3px dashed #667eea;
                border-radius: 10px;
                padding: 40px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s;
                margin-bottom: 20px;
                background: #f8f9ff;
            }
            .upload-area:hover {
                border-color: #764ba2;
                background: #f0f2ff;
            }
            .upload-area.dragover {
                border-color: #764ba2;
                background: #e8ebff;
                transform: scale(1.02);
            }
            input[type="file"] {
                display: none;
            }
            .upload-icon {
                font-size: 3em;
                margin-bottom: 10px;
            }
            .btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 1em;
                font-weight: 600;
                transition: transform 0.2s;
                width: 100%;
                margin-top: 10px;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }
            .btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            #preview {
                max-width: 100%;
                max-height: 300px;
                border-radius: 10px;
                margin: 20px auto;
                display: none;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
            #result {
                margin-top: 30px;
                padding: 20px;
                background: #f8f9ff;
                border-radius: 10px;
                border-left: 4px solid #667eea;
                display: none;
                white-space: pre-wrap;
                font-family: 'Courier New', monospace;
                max-height: 400px;
                overflow-y: auto;
                line-height: 1.6;
            }
            .loading {
                display: none;
                text-align: center;
                margin: 20px 0;
            }
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .file-name {
                margin: 10px 0;
                color: #667eea;
                font-weight: 600;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📜 Transcriptor Paleográfico</h1>
            <p class="subtitle">Transcribe manuscritos de la Nueva España del siglo XVI</p>
            
            <div class="upload-area" id="uploadArea" onclick="document.getElementById('fileInput').click()">
                <div class="upload-icon">📄</div>
                <p><strong>Haz clic</strong> o arrastra una imagen aquí</p>
                <p style="color: #666; font-size: 0.9em; margin-top: 10px;">Formatos: JPG, PNG, WEBP</p>
            </div>
            
            <input type="file" id="fileInput" accept="image/*">
            
            <div class="file-name" id="fileName"></div>
            
            <img id="preview" alt="Vista previa">
            
            <button class="btn" id="transcribeBtn" onclick="transcribe()" disabled>
                Transcribir Manuscrito
            </button>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p style="margin-top: 10px; color: #667eea;">Transcribiendo...</p>
            </div>
            
            <div id="result"></div>
        </div>

        <script>
            let selectedFile = null;
            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');
            const preview = document.getElementById('preview');
            const fileName = document.getElementById('fileName');
            const transcribeBtn = document.getElementById('transcribeBtn');
            const loading = document.getElementById('loading');
            const result = document.getElementById('result');

            // Prevenir comportamiento por defecto del navegador
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                uploadArea.addEventListener(eventName, preventDefaults, false);
            });

            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }

            // Efectos visuales para drag and drop
            ['dragenter', 'dragover'].forEach(eventName => {
                uploadArea.addEventListener(eventName, () => {
                    uploadArea.classList.add('dragover');
                });
            });

            ['dragleave', 'drop'].forEach(eventName => {
                uploadArea.addEventListener(eventName, () => {
                    uploadArea.classList.remove('dragover');
                });
            });

            // Manejar drop
            uploadArea.addEventListener('drop', (e) => {
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    handleFile(files[0]);
                }
            });

            // Manejar selección de archivo
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    handleFile(e.target.files[0]);
                }
            });

            function handleFile(file) {
                if (!file.type.startsWith('image/')) {
                    alert('Por favor selecciona una imagen válida');
                    return;
                }

                selectedFile = file;
                fileName.textContent = '📎 ' + file.name;
                
                // Mostrar vista previa
                const reader = new FileReader();
                reader.onload = (e) => {
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                };
                reader.readAsDataURL(file);

                transcribeBtn.disabled = false;
                result.style.display = 'none';
            }

            async function transcribe() {
                if (!selectedFile) {
                    alert('Por favor selecciona una imagen primero');
                    return;
                }

                const formData = new FormData();
                formData.append('file', selectedFile);

                transcribeBtn.disabled = true;
                loading.style.display = 'block';
                result.style.display = 'none';

                try {
                    const response = await fetch('/transcribe', {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();

                    if (data.success) {
                        result.textContent = data.text;
                        result.style.display = 'block';
                    } else {
                        alert('Error en la transcripción');
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                } finally {
                    loading.style.display = 'none';
                    transcribeBtn.disabled = false;
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):

    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes))

    prompt = """
    Actúa como un experto paleógrafo. Transcribe el texto de esta imagen 
    procedente de la Nueva España del siglo XVI. 
    1. Proporciona una transcripción diplomática (fiel al original).
    2. Desarrolla las abreviaturas entre paréntesis.
    3. Si una palabra es ilegible, coloca [ilegible].

    Transcribe fielmente este manuscrito histórico en español del siglo XVI.
    Reglas:

    - Mantén ortografía original
    - Mantén saltos de línea
    - No modernices el texto
    - No agregues texto que no exista
    - Si algo es ilegible, escribe [ilegible]
    - Regresa solo el texto transcrito, sin explicaciones ni comentarios adicionales.
    """

    response = model.generate_content([prompt, image])

    return {
        "success": True,
        "text": response.text
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
