import base64
import datetime
import os
import requests
from fastapi import APIRouter, HTTPException

from app.models.schemas import SaveLocalRequest, OfflineAttendanceRequest
from app.database.sqlite import (
    save_huella_local,
    get_all_huellas_locales,
    save_asistencia_offline,
    get_asistencias_offline,
    clear_asistencias_offline,
    clear_huellas_locales
)
from app.services.biomini import biomini_service, hardware_status

router = APIRouter(prefix="/api/biomini", tags=["biomini"])

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3000")

def sync_huellas_from_backend():
    print(f"🔄 Sincronizando huellas desde el servidor central: {BACKEND_URL}...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/trabajadores/huellas", timeout=5)
        if response.status_code == 200:
            clear_huellas_locales()
            huellas_remotas = response.json()
            for item in huellas_remotas:
                tid = item["trabajador_id"]
                template_b64 = item["huella_template"]
                template_bytes = base64.b64decode(template_b64)
                save_huella_local(tid, template_bytes)
            print(f"✅ Sincronización exitosa. {len(huellas_remotas)} huellas importadas a SQLite local.")
        else:
            print(f"⚠️  El servidor respondió con código {response.status_code}. Se iniciará con huellas guardadas localmente.")
    except Exception as e:
        print(f"⚠️  No se pudo conectar al Backend para sincronización ({str(e)}). Iniciando en modo offline con datos locales.")

@router.get("/status")
def get_hardware_status():
    return hardware_status

@router.post("/sync")
def trigger_sync():
    sync_huellas_from_backend()
    return {"status": "success", "message": "Sincronización forzada completada"}

@router.post("/enroll")
def enroll_fingerprint():
    try:
        # Captura la huella usando el servicio
        template_bytes = biomini_service.enroll()
        
        # Verificar duplicados locales
        stored_huellas = get_all_huellas_locales()
        for trabajador_id, stored_bytes in stored_huellas:
            try:
                if biomini_service.verify_match(template_bytes, stored_bytes):
                    template_b64 = base64.b64encode(template_bytes).decode("utf-8")
                    return {
                        "status": "duplicate",
                        "trabajador_id": trabajador_id,
                        "huella_template": template_b64,
                        "message": f"Esta huella ya pertenece al trabajador con ID {trabajador_id}"
                    }
            except Exception as match_err:
                print(f"Error al verificar coincidencia en enroll: {match_err}")
        
        # Convertir los bytes a string Base64 para el Frontend
        template_b64 = base64.b64encode(template_bytes).decode("utf-8")
        
        return {
            "status": "success",
            "huella_template": template_b64
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(e)})

@router.post("/save-local")
def save_local(data: SaveLocalRequest):
    try:
        template_bytes = base64.b64decode(data.huella_template)
        save_huella_local(data.trabajador_id, template_bytes)
        return {
            "status": "success",
            "message": "Huella vinculada y almacenada localmente con éxito"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail={"status": "error", "message": f"Error al decodificar o guardar: {str(e)}"})

@router.post("/identify")
def identify_fingerprint():
    try:
        # Capturar huella actual
        captured_bytes = biomini_service.enroll()
        
        # Recuperar todas las huellas de SQLite local
        stored_huellas = get_all_huellas_locales()
        
        if not stored_huellas:
            return {
                "status": "success",
                "identificado": False,
                "message": "No hay huellas registradas en la base de datos local."
            }

        # Comparar la huella capturada contra cada una en la DB (Búsqueda 1:N)
        for trabajador_id, stored_bytes in stored_huellas:
            if biomini_service.verify_match(captured_bytes, stored_bytes):
                return {
                    "status": "success",
                    "trabajador_id": trabajador_id,
                    "identificado": True
                }

        # Si no hubo coincidencias
        return {
            "status": "success",
            "identificado": False
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(e)})

@router.post("/save-offline")
def save_offline_attendance(data: OfflineAttendanceRequest):
    try:
        now = datetime.datetime.now()
        fecha_str = now.strftime("%Y-%m-%d")
        hora_str = now.strftime("%H:%M:%S")
        
        save_asistencia_offline(data.trabajador_id, fecha_str, hora_str)
        return {
            "status": "success",
            "message": f"Asistencia del trabajador ID {data.trabajador_id} almacenada en contingencia local ({fecha_str} {hora_str})"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(e)})

@router.get("/offline-attendance")
def get_offline_records():
    records = get_asistencias_offline()
    return records

@router.delete("/offline-attendance")
def clear_offline_records():
    try:
        clear_asistencias_offline()
        return {
            "status": "success",
            "message": "Contingencia de asistencia limpiada correctamente"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(e)})
