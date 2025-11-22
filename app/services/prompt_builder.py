# app/services/prompt_builder.py
from app.models.case_model import TestCase
import os
import re
import json

class PromptBuilder:
    """
    Construye prompts optimizados usando templates específicos para cada tipo de test.
    """
    
    def __init__(self):
        self.templates_dir = "app/templates"
        self._ensure_templates_exist()
    
    def _ensure_templates_exist(self):
        """Verifica que existan los templates necesarios"""
        os.makedirs(self.templates_dir, exist_ok=True)
    
    def build_prompt(self, test_case: TestCase) -> str:
        """
        Genera un prompt usando el template apropiado según el tipo de test.
        
        Args:
            test_case: Caso de prueba con información del test
            
        Returns:
            Prompt formateado y listo para enviar a Manus IA
        """
        # Detectar tipo de test
        test_type = self._detect_test_type(test_case)
        
        print(f"🎯 Tipo de test detectado: {test_type}")
        
        # Cargar template correspondiente
        template = self._load_template(test_type)
        
        # Extraer datos del test case
        test_data = self._extract_test_data(test_case, test_type)
        
        # Formatear template con los datos
        try:
            prompt = template.format(**test_data)
            print(f"✅ Prompt generado ({len(prompt)} chars)")
            return prompt
        except KeyError as e:
            print(f"⚠️ Error al formatear template: {e}")
            return self._build_fallback_prompt(test_case)
    
    def _detect_test_type(self, test_case: TestCase) -> str:
        """
        Detecta el tipo de test basándose en el contenido del caso de prueba.
        """
        text = f"{test_case.name} {test_case.description} {test_case.steps}".lower()
        
        # 1. Login con credenciales incorrectas
        if any(keyword in text for keyword in ['incorrecta', 'incorrect', 'inválida', 'invalid', 'fallido', 'failed']) and \
           any(keyword in text for keyword in ['login', 'contraseña', 'password', 'credencial']):
            return "login_invalid_credentials"
        
        # 2. Registro de usuario
        elif any(keyword in text for keyword in ['registr', 'register', 'sign up', 'crear cuenta', 'nueva cuenta', 'crea tu cuenta']):
            return "user_registration"
        
        # 3. Búsqueda
        elif any(keyword in text for keyword in ['buscar', 'search', 'búsqueda']):
            return "search_functionality"
        
        # 4. Logout
        elif any(keyword in text for keyword in ['logout', 'cerrar sesión', 'salir', 'sign out']):
            return "cerrar_sesion_prompt"
        
        # 5. Google OAuth
        elif any(keyword in text for keyword in ['google', 'oauth', 'auth', 'sso', 'continuar con google']):
            return "google_oauth_login"
        
        # 6. Login tradicional
        elif any(keyword in text for keyword in ['login', 'iniciar sesión', 'usuario', 'contraseña', 'password']):
            has_user = bool(re.search(r'usuario[:\s]+\w+', text, re.IGNORECASE))
            has_pass = bool(re.search(r'(contraseña|password)[:\s]+\w+', text, re.IGNORECASE))
            
            if has_user and has_pass:
                return "traditional_login"
            else:
                return "google_oauth_login"
        
        # 7. Navegación
        elif any(keyword in text for keyword in ['navegación', 'navigate', 'visitar', 'ir a', 'módulo', 'sección']):
            return "navigation"
        
        # 8. Formulario
        elif any(keyword in text for keyword in ['formulario', 'form', 'llenar', 'submit']):
            return "form_submission"
        
        else:
            if test_case.url and 'login' in test_case.url.lower():
                return "google_oauth_login"
            return "navigation"
    
    def _load_template(self, test_type: str) -> str:
        """
        Carga el template correspondiente al tipo de test.
        
        Args:
            test_type: Tipo de test detectado
            
        Returns:
            Contenido del template
        """
        template_path = os.path.join(self.templates_dir, f"{test_type}.txt")
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            print(f"✅ Template cargado: {test_type}.txt")
            return template_content
        except FileNotFoundError:
            print(f"⚠️ Template no encontrado: {template_path}")
            print(f"📝 Usando template por defecto")
            return self._get_default_template(test_type)
    
    def _extract_test_data(self, test_case: TestCase, test_type: str) -> dict:
        """
        Extrae los datos necesarios del test case según el tipo de test.
        
        Returns:
            Diccionario con variables para formatear el template
        """
        # Parsear input_data si es JSON string
        input_data = {}
        if test_case.steps:
            try:
                input_data = json.loads(test_case.steps)
            except (json.JSONDecodeError, TypeError):
                # Si no es JSON, mantener como texto
                pass
        
        # Datos base comunes para todos los templates
        data = {
            "url": input_data.get("url") or test_case.url or "https://www.celevro.com",
            "expected_result": test_case.expected_result or "Acción completada exitosamente",
            "test_name": test_case.name or "Test sin nombre",
            "description": test_case.description or ""
        }
        
        # Datos específicos según el tipo de test
        if test_type == "google_oauth_login":
            data["email"] = input_data.get("email") or self._extract_email(test_case) or "andersonveelezca@gmail.com"
            data["oauth_provider"] = "Google"
        
        elif test_type == "login_invalid_credentials":
            data["username"] = input_data.get("username") or "usuario_invalido"
            data["password"] = input_data.get("password") or "password_incorrecta"
            data["expected_error"] = "Credenciales incorrectas"
        
        elif test_type == "traditional_login":
            data["username"] = input_data.get("username") or self._extract_username(test_case) or "testuser"
            data["password"] = input_data.get("password") or self._extract_password(test_case) or "Test123!"
        
        elif test_type == "user_registration":
            data["fullname"] = input_data.get("fullname") or self._extract_fullname(test_case) or "Juan"
            data["lastname"] = input_data.get("lastname") or self._extract_lastname(test_case) or "Pérez"
            data["email"] = input_data.get("email") or self._extract_email(test_case) or "testuser@example.com"
            data["username"] = input_data.get("username") or self._extract_username(test_case) or "testuser123"
            data["password"] = input_data.get("password") or self._extract_password(test_case) or "Test123!@#"
            data["confirm_password"] = input_data.get("confirm_password") or data["password"]
            data["gender"] = input_data.get("gender") or "Masculino"
            
            # Fecha de nacimiento
            birthdate = input_data.get("birthdate", {})
            if isinstance(birthdate, dict):
                data["birthdate_day"] = birthdate.get("day", "15")
                data["birthdate_month"] = birthdate.get("month", "06")
                data["birthdate_year"] = birthdate.get("year", "1990")
            else:
                data["birthdate_day"] = "15"
                data["birthdate_month"] = "06"
                data["birthdate_year"] = "1990"
        
        elif test_type == "search_functionality":
            data["search_term"] = input_data.get("search_term") or self._extract_search_term(test_case) or "producto test"
        
        elif test_type == "navigation":
            sections = input_data.get("sections") or self._extract_sections(test_case)
            data["sections"] = sections if sections else "Home,Productos,Contacto"
        
        elif test_type == "logout":
            # Logout solo necesita URL
            pass
        
        return data
    
    def _extract_email(self, test_case: TestCase) -> str:
        """Extrae email del test case"""
        text = f"{test_case.steps} {test_case.description}"
        
        # Buscar patrón de email
        email_match = re.search(r'\b[\w.-]+@[\w.-]+\.\w+\b', text)
        if email_match:
            return email_match.group(0)
        
        # Buscar "Email: xxx" o "Correo: xxx"
        email_pattern = re.search(r'(?:e?mail|correo)[:\s]+([^\s,;]+@[^\s,;]+)', text, re.IGNORECASE)
        if email_pattern:
            return email_pattern.group(1)
        
        return None
    
    def _extract_username(self, test_case: TestCase) -> str:
        """Extrae username del test case"""
        text = f"{test_case.steps} {test_case.description}"
        
        username_pattern = re.search(r'(?:usuario|username|user)[:\s]+([^\s,;]+)', text, re.IGNORECASE)
        if username_pattern:
            return username_pattern.group(1)
        
        return None
    
    def _extract_password(self, test_case: TestCase) -> str:
        """Extrae password del test case"""
        text = f"{test_case.steps} {test_case.description}"
        
        password_pattern = re.search(r'(?:contraseña|password|clave)[:\s]+([^\s,;]+)', text, re.IGNORECASE)
        if password_pattern:
            return password_pattern.group(1)
        
        return None
    
    def _extract_fullname(self, test_case: TestCase) -> str:
        """Extrae nombre completo del test case"""
        text = f"{test_case.steps} {test_case.description}"
        
        # Buscar "Nombre: xxx" o "Fullname: xxx"
        name_pattern = re.search(r'(?:nombre|fullname|name)[:\s]+([A-Za-záéíóúÁÉÍÓÚñÑ\s]+?)(?:,|;|\.|$)', text, re.IGNORECASE)
        if name_pattern:
            return name_pattern.group(1).strip()
        
        return None
    
    def _extract_lastname(self, test_case: TestCase) -> str:
        """Extrae apellido del test case"""
        text = f"{test_case.steps} {test_case.description}"
        
        lastname_pattern = re.search(r'(?:apellido|lastname|surname)[:\s]+([A-Za-záéíóúÁÉÍÓÚñÑ\s]+?)(?:,|;|\.|$)', text, re.IGNORECASE)
        if lastname_pattern:
            return lastname_pattern.group(1).strip()
        
        return None
    
    def _extract_search_term(self, test_case: TestCase) -> str:
        """Extrae término de búsqueda del test case"""
        text = f"{test_case.steps} {test_case.description}"
        
        search_pattern = re.search(r'(?:buscar|search)[:\s]+([^,;.]+)', text, re.IGNORECASE)
        if search_pattern:
            return search_pattern.group(1).strip()
        
        return None
    
    def _extract_sections(self, test_case: TestCase) -> str:
        """Extrae secciones a visitar del test case"""
        text = f"{test_case.steps} {test_case.description}"
        
        sections_pattern = re.search(r'(?:secciones|módulos|sections)[:\s]+([^.]+)', text, re.IGNORECASE)
        if sections_pattern:
            return sections_pattern.group(1).strip()
        
        return None
    
    def _get_default_template(self, test_type: str) -> str:
        """
        Template por defecto cuando no existe el archivo.
        """
        return '''
SISTEMA DE EJECUCIÓN AUTOMÁTICA - SOLO CÓDIGO PYTHON

⚠️ ADVERTENCIA: Este es un sistema automatizado que ejecuta código directamente.
Tu respuesta será interpretada como código Python y ejecutada sin intervención humana.

PROHIBIDO ABSOLUTAMENTE:
❌ Escribir "Entendido"
❌ Escribir "Aquí está el código"
❌ Escribir "Voy a generar..."
❌ Análisis o reportes
❌ Explicaciones antes o después del código
❌ Usar markdown ```python```

OBLIGATORIO:
✅ Tu PRIMERA LÍNEA debe ser exactamente: # Configuración
✅ Solo código Python válido
✅ Sin ningún texto adicional

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TEST: {test_name}
URL: {url}
ESPERADO: {expected_result}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GENERA AHORA (tu respuesta completa debe ser código ejecutable):

# Configuración
url = "{url}"

print("=" * 80)
print("🚀 INICIO: {test_name}")
print("=" * 80)

print("\\n📍 PASO 1: Navegando a la página")
driver.get(url)
time.sleep(3)
driver.execute_script("document.body.style.border='5px solid blue';")
print(f"✅ Página cargada: {{driver.title}}")
save_screenshot()
time.sleep(2)

print("\\n📍 PASO 2: Analizando elementos")
try:
    buttons = driver.find_elements(By.XPATH, "//button | //a[@href] | //input[@type='submit']")
    print(f"✅ Elementos encontrados: {{len(buttons)}}")
    
    if buttons:
        first_button = buttons[0]
        driver.execute_script("arguments[0].style.border='3px solid orange'; arguments[0].scrollIntoView({{block: 'center'}});", first_button)
        print(f"✅ Primer elemento: {{first_button.text or 'Sin texto'}}")
        save_screenshot()
        time.sleep(2)
        
except Exception as e:
    print(f"⚠️ Error: {{e}}")

print("\\n📍 PASO 3: Validación")
save_screenshot()
current_url = driver.current_url
print(f"🔗 URL: {{current_url}}")
print(f"📄 Título: {{driver.title}}")

driver.execute_script("""
    var div = document.createElement('div');
    div.innerHTML = '✅ TEST COMPLETADO';
    div.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:green;color:white;padding:40px;font-size:28px;z-index:10000;border-radius:15px;';
    document.body.appendChild(div);
""")

time.sleep(3)
print("\\n🏁 FIN: {test_name}")
print("=" * 80)
'''
    
    def _build_fallback_prompt(self, test_case: TestCase) -> str:
        """
        Prompt de emergencia si falla todo lo demás.
        Este se usa cuando hay error en el formateo del template.
        """
        return f'''
SOLO GENERA CÓDIGO PYTHON EJECUTABLE. NO agregues explicaciones.

Tu respuesta DEBE comenzar con: # Configuración

Test a automatizar:
- Nombre: {test_case.name}
- URL: {test_case.url or 'https://www.celevro.com'}
- Descripción: {test_case.description or 'Sin descripción'}
- Pasos: {test_case.steps or 'Automatizar el flujo completo'}
- Resultado Esperado: {test_case.expected_result or 'Ejecución exitosa'}

GENERA:
1. Navegación a {test_case.url or 'https://www.celevro.com'}
2. Interacción con elementos visibles
3. Resaltado con driver.execute_script()
4. Screenshots con save_screenshot()
5. Validación final con print()

Variables disponibles: driver, By, Keys, time, WebDriverWait, EC, save_screenshot()

IMPORTANTE: No uses markdown (```python```), no agregues títulos, solo código Python puro.
'''
