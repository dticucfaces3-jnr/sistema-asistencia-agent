import logging
import sys

# Configurar logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("biomini_service")

# Intentar importar la librería. Si falla, configuramos una variable indicando el error.
BIOMINI_AVAILABLE = False
biomini_import_error = None

try:
    from biomini import Biomini, match_templates
    BIOMINI_AVAILABLE = True
except Exception as e:
    biomini_import_error = e
    logger.error(
        "⚠️  No se pudo cargar la librería 'python-biomini' o sus dependencias de .NET (.dll).\n"
        f"Detalle del error: {str(e)}\n"
        "REQUISITOS MÍNIMOS:\n"
        "1. Asegúrate de instalar pythonnet: pip install pythonnet\n"
        "2. Copia los archivos del SDK de Suprema (.dll) en la carpeta del agente:\n"
        "   - Suprema.UFScanner.dll\n"
        "   - Suprema.UFMatcher.dll\n"
        "   - UFScanner.dll\n"
        "   - UFMatcher.dll\n"
        "3. El bitness de tu instalación de Python (32/64 bits) DEBE coincidir con el de las DLLs de Suprema."
    )

hardware_status = {"connected": False}

class BiominiService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(BiominiService, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.device = None
        if not BIOMINI_AVAILABLE:
            self.initialization_error = (
                "El agente de huellas no está operativo. El módulo 'python-biomini' no está disponible "
                f"debido a la falta de DLLs de Suprema o incompatibilidad de arquitectura. Error: {str(biomini_import_error)}"
            )
            logger.error(self.initialization_error)
            return

        try:
            self.device = Biomini()
            self.initialization_error = None
            logger.info("✅ Suprema BioMini SDK inicializado a través de python-biomini.")
        except Exception as e:
            self.initialization_error = f"Error al inicializar el SDK de Biomini: {str(e)}"
            logger.error(self.initialization_error)

    def is_connected(self) -> bool:
        """Verifica si hay lectores conectados, actualizando el estado."""
        if self.initialization_error or not self.device:
            return False
        try:
            num_scanners = self.device.detect_scanners()
            return num_scanners > 0
        except Exception:
            return False

    def _ensure_scanner(self):
        """Verifica que el SDK esté inicializado y que exista al menos un escáner conectado."""
        if self.initialization_error:
            raise Exception(self.initialization_error)
        
        num_scanners = self.device.detect_scanners()
        if num_scanners <= 0:
            raise Exception("No se detectaron lectores BioMini conectados por USB en este equipo.")
        
        # Asignamos el primer escáner detectado como el actual
        scanners = self.device.scanners()
        self.device.current_scanner = scanners[0]
        return scanners[0]

    def enroll(self) -> bytes:
        """Activa el lector, captura una huella y devuelve el template binario (bytes)."""
        self._ensure_scanner()
        logger.info("Fingerprint scanner enrolleing started...")
        
        # Llamar al método enroll de python-biomini
        enroll_result = self.device.enroll()
        
        if not enroll_result or not hasattr(enroll_result, 'success') or not enroll_result.success:
            error_msg = getattr(enroll_result, 'error_message', 'Error desconocido durante la captura')
            raise Exception(f"Captura fallida: {error_msg}")
        
        # Retorna el template capturado
        return bytes(enroll_result.template)

    def verify_match(self, template_captured: bytes, template_stored: bytes) -> bool:
        """Compara dos huellas y determina si coinciden."""
        if self.initialization_error:
            raise Exception(self.initialization_error)
        
        try:
            # Usar la función match_templates provista por python-biomini
            # Convierte los parámetros a bytearray/bytes adecuados si es necesario
            return match_templates(bytes(template_captured), bytes(template_stored))
        except Exception as e:
            logger.error(f"Error durante la comparación de huellas: {str(e)}")
            return False

# Instancia única del servicio
biomini_service = BiominiService()
