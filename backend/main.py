from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uuid
import os
import whisper
import tempfile
import traceback

app = FastAPI()

# CORS middleware - MUST be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins like ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists
os.makedirs("uploads", exist_ok=True)

# Load Whisper model (base model - good balance of speed and accuracy)
# Model is loaded once at startup for better performance
_whisper_model = None

def check_ffmpeg():
    """Check if FFmpeg is installed (required by Whisper)"""
    import subprocess
    import shutil
    try:
        # First check if ffmpeg is in PATH
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            print(f"✓ FFmpeg found at: {ffmpeg_path}")
            # Verify it works
            result = subprocess.run(['ffmpeg', '-version'], 
                          capture_output=True, 
                          check=True, 
                          timeout=5)
            print("✓ FFmpeg is working correctly")
            return True
        else:
            raise FileNotFoundError("FFmpeg not in PATH")
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        print("⚠ WARNING: FFmpeg not found. Whisper requires FFmpeg to process audio files.")
        print("  Please install FFmpeg:")
        print("  - Windows: Download from https://www.gyan.dev/ffmpeg/builds/")
        print("            Or use: winget install ffmpeg")
        print("            Or use: choco install ffmpeg")
        print("  - Make sure to add FFmpeg to your system PATH")
        print("  - Restart your terminal/server after installation")
        print("  - Verify with: ffmpeg -version")
        return False

def get_whisper_model():
    """Lazy load Whisper model to avoid loading on import"""
    global _whisper_model
    if _whisper_model is None:
        print("Loading Whisper model...")
        try:
            _whisper_model = whisper.load_model("base")
            print("Whisper model loaded successfully")
        except Exception as e:
            print(f"Error loading Whisper model: {e}")
            raise
    return _whisper_model

# Check FFmpeg on startup
check_ffmpeg()

async def transcribe_with_whisper(audio_bytes: bytes, filename: str = None, content_type: str = None) -> str:
    """
    Transcribe audio using OpenAI Whisper library.
    """
    temp_file_path = None
    try:
        # Determine file extension based on content type or filename
        suffix = '.wav'  # default
        if content_type:
            if 'webm' in content_type.lower():
                suffix = '.webm'
            elif 'mp3' in content_type.lower():
                suffix = '.mp3'
            elif 'm4a' in content_type.lower():
                suffix = '.m4a'
            elif 'ogg' in content_type.lower():
                suffix = '.ogg'
        elif filename:
            # Extract extension from filename
            _, ext = os.path.splitext(filename.lower())
            if ext:
                suffix = ext
        
        # Create a temporary file to save the audio bytes
        # Whisper requires a file path, not raw bytes
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name
        
        print(f"Saved audio to temporary file: {temp_file_path} (size: {len(audio_bytes)} bytes)")
        
        # Verify FFmpeg is available before attempting transcription
        import shutil
        if not shutil.which('ffmpeg'):
            raise FileNotFoundError(
                "FFmpeg is not installed or not in PATH. "
                "Please install FFmpeg and restart the server."
            )
        
        # Load the Whisper model
        print("Loading Whisper model...")
        model = get_whisper_model()
        
        # Transcribe the audio file
        print(f"Transcribing audio file: {temp_file_path}")
        result = model.transcribe(temp_file_path)
        
        # Extract the text from the result
        transcription_text = result["text"].strip()
        
        print(f"Transcription completed. Length: {len(transcription_text)} characters")
        
        return transcription_text
        
    except (FileNotFoundError, OSError) as e:
        # Check if this is an FFmpeg-related error
        error_str = str(e).lower()
        if 'winerror 2' in error_str or 'cannot find the file' in error_str or 'ffmpeg' in error_str:
            error_msg = (
                "FFmpeg not found. Whisper requires FFmpeg to process audio files.\n\n"
                "Please install FFmpeg:\n"
                "- Windows: Download from https://www.gyan.dev/ffmpeg/builds/ or use: winget install ffmpeg\n"
                "- Make sure FFmpeg is added to your system PATH\n"
                "- Restart your terminal/server after installation\n"
                "- Verify with: ffmpeg -version"
            )
        else:
            error_msg = f"File system error: {str(e)}"
        print(f"Error in transcribe_with_whisper: {error_msg}")
        print(f"Original error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)
    except ImportError as e:
        error_msg = f"Whisper library not installed. Please run: pip install openai-whisper"
        print(f"Error in transcribe_with_whisper: {error_msg}")
        print(f"Original error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Transcription failed: {str(e)}"
        print(f"Error in transcribe_with_whisper: {error_msg}")
        print(f"Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                print(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as cleanup_error:
                print(f"Warning: Could not delete temporary file {temp_file_path}: {cleanup_error}")

async def enhance_with_ai(transcription: str) -> str:
    """
    Enhance transcription using AI to fill in gaps.
    This is a placeholder - you'll need to implement actual AI enhancement.
    """
    try:
        # TODO: Implement actual AI enhancement
        # This could use OpenAI GPT, Claude, or another AI service
        # to improve the transcription quality
        
        # For now, return the transcription as-is
        return transcription
    except Exception as e:
        print(f"Error in enhance_with_ai: {e}")
        raise HTTPException(status_code=500, detail=f"Enhancement failed: {str(e)}")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler to ensure CORS headers are always sent"""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.post("/upload/")
async def upload_audio(file: UploadFile = File(...)):
    try:
        # Save uploaded file
        file_id = str(uuid.uuid4())
        file_path = f"uploads/{file_id}_{file.filename}"
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return {"file_id": file_id, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/transcribe/")
async def transcribe_audio(audio: UploadFile = File(...)):
    try:
        print(f"Received audio file: {audio.filename}, content-type: {audio.content_type}")
        contents = await audio.read()
        print(f"Audio file size: {len(contents)} bytes")
        
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        transcription = await transcribe_with_whisper(contents, filename=audio.filename, content_type=audio.content_type)
        return {"original_transcript": transcription}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Transcription error: {str(e)}"
        print(f"Error in transcribe_audio: {error_msg}")
        print(f"Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/enhance/")
async def enhance_transcription(transcription: str):
    try:
        if not transcription:
            raise HTTPException(status_code=400, detail="Transcription text is required")
        
        enhanced = await enhance_with_ai(transcription)
        return {"enhanced_transcription": enhanced}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in enhance_transcription: {e}")
        raise HTTPException(status_code=500, detail=f"Enhancement error: {str(e)}")


