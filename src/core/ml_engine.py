"""
SMARTFIX Tool Enforcement - Motor de Inteligencia Artificial
Módulo principal para análisis de código y generación de soluciones
"""

import logging
import json
from typing import Dict, List, Any, Optional
import requests
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import re

class SmartFixAIEngine:
    """Motor de IA para análisis y reparación de código"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("smartfix.ml_engine")
        self.tokenizer = None
        self.model = None
        self.initialized = False
        
    def initialize(self):
        """Inicializar el motor de IA"""
        try:
            self.logger.info("Inicializando motor de IA...")
            
            # Cargar modelo local si está disponible
            if self.config.get("use_local_model", False):
                model_path = self.config.get("local_model_path")
                if model_path:
                    self.logger.info(f"Cargando modelo local desde: {model_path}")
                    self.tokenizer = AutoTokenizer.from_pretrained(model_path)
                    self.model = AutoModelForCausalLM.from_pretrained(
                        model_path,
                        torch_dtype=torch.float16,
                        device_map="auto"
                    )
                else:
                    self.logger.warning("Ruta de modelo local no configurada")
            
            self.initialized = True
            self.logger.info("Motor de IA inicializado correctamente")
            
        except Exception as e:
            self.logger.error(f"Error inicializando motor de IA: {str(e)}")
            raise
    
    def analyze_code(self, code: str, language: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analizar código en busca de problemas y generar soluciones
        
        Args:
            code: Código a analizar
            language: Lenguaje de programación
            context: Contexto adicional del análisis
            
        Returns:
            Dict con resultados del análisis
        """
        try:
            if not self.initialized:
                self.initialize()
            
            self.logger.info(f"Analizando código {language} (longitud: {len(code)})")
            
            # Construir prompt para análisis
            prompt = self._build_analysis_prompt(code, language, context)
            
            # Obtener análisis del modelo
            if self.model and self.tokenizer:
                # Usar modelo local
                analysis = self._analyze_with_local_model(prompt)
            else:
                # Usar API externa (DeepSeek)
                analysis = self._analyze_with_api(prompt)
            
            # Procesar y validar resultados
            processed_analysis = self._process_analysis_results(analysis, code, language)
            
            self.logger.info(f"Análisis completado. Problemas encontrados: {len(processed_analysis.get('issues', []))}")
            
            return processed_analysis
            
        except Exception as e:
            self.logger.error(f"Error en análisis de código: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "issues": []
            }
    
    def _build_analysis_prompt(self, code: str, language: str, context: Dict[str, Any] = None) -> str:
        """Construir prompt para análisis de código"""
        base_prompt = f"""
Como experto en análisis de código {language}, analiza el siguiente código y proporciona:

1. LISTA DE PROBLEMAS: Identifica todos los errores, vulnerabilidades y oportunidades de mejora
2. NIVEL DE SEVERIDAD: Para cada problema (crítico, alto, medio, bajo)
3. EXPLICACIÓN: Breve explicación de cada problema
4. SOLUCIÓN: Código corregido para cada problema
5. CATEGORÍA: Tipo de problema (seguridad, rendimiento, sintaxis, lógica, etc.)

CÓDIGO A ANALIZAR:
```{language}
{code}
"""

        if context:
            context_str = json.dumps(context, indent=2)
            base_prompt += f"\nCONTEXTO ADICIONAL:\n{context_str}"
        
        base_prompt += "\n\nRESPONDE SOLO CON JSON VÁLIDO con el siguiente formato:\n"
        base_prompt += '''
{
  "analysis_id": "string",
  "success": true,
  "issues": [
    {
      "id": "string",
      "type": "error|warning|improvement",
      "severity": "critical|high|medium|low",
      "category": "security|performance|syntax|logic|best_practice",
      "description": "string",
      "line": number,
      "column": number,
      "code_snippet": "string",
      "solution": "string",
      "confidence": number
    }
  ],
  "summary": {
    "total_issues": number,
    "critical_issues": number,
    "security_issues": number,
    "estimated_time_to_fix": number
  }
}
'''
        
        return base_prompt
    
    def _analyze_with_local_model(self, prompt: str) -> Dict[str, Any]:
        """Analizar usando modelo local"""
        try:
            inputs = self.tokenizer.encode(prompt, return_tensors="pt")
            
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=len(inputs[0]) + 512,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extraer JSON de la respuesta
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"success": False, "error": "No se pudo extraer JSON de la respuesta"}
                
        except Exception as e:
            self.logger.error(f"Error en análisis con modelo local: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _analyze_with_api(self, prompt: str) -> Dict[str, Any]:
        """Analizar usando API externa (DeepSeek)"""
        try:
            headers = {
                "Authorization": f"Bearer {self.config.get('deepseek_api_key')}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.config.get("ai_model", "deepseek-coder"),
                "messages": [
                    {
                        "role": "system",
                        "content": "Eres un experto en análisis y reparación de código. Responde solo con JSON válido."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            content = result["choices"][0]["message"]["content"]
            
            # Extraer JSON de la respuesta
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"success": False, "error": "No se pudo extraer JSON de la respuesta"}
                
        except Exception as e:
            self.logger.error(f"Error en análisis con API: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _process_analysis_results(self, analysis: Dict[str, Any], original_code: str, language: str) -> Dict[str, Any]:
        """Procesar y validar resultados del análisis"""
        try:
            if not analysis.get("success", False):
                return analysis
            
            # Validar estructura básica
            if "issues" not in analysis:
                analysis["issues"] = []
            
            # Procesar cada issue
            for issue in analysis["issues"]:
                # Asegurar campos obligatorios
                issue.setdefault("id", self._generate_issue_id())
                issue.setdefault("confidence", 0.8)
                issue.setdefault("category", "unknown")
                
                # Validar solución
                if "solution" in issue:
                    issue["solution"] = self._validate_solution(issue["solution"], original_code, language)
            
            # Calcular métricas de resumen
            analysis["summary"] = self._calculate_summary_metrics(analysis["issues"])
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error procesando resultados: {str(e)}")
            return {
                "success": False,
                "error": f"Error procesando resultados: {str(e)}",
                "issues": []
            }
    
    def _generate_issue_id(self) -> str:
        """Generar ID único para issue"""
        import uuid
        return f"issue_{uuid.uuid4().hex[:8]}"
    
    def _validate_solution(self, solution: str, original_code: str, language: str) -> str:
        """Validar y formatear solución"""
        # Eliminar markdown code blocks si existen
        solution = re.sub(r'```.*?\n', '', solution)
        solution = re.sub(r'\n```', '', solution)
        
        # Para soluciones completas, asegurar formato adecuado
        if language and not solution.startswith(f"```{language}"):
            solution = f"```{language}\n{solution.strip()}\n```"
        
        return solution
    
    def _calculate_summary_metrics(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcular métricas de resumen del análisis"""
        severity_count = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        category_count = {}
        
        for issue in issues:
            severity = issue.get("severity", "medium").lower()
            category = issue.get("category", "unknown").lower()
            
            if severity in severity_count:
                severity_count[severity] += 1
            
            category_count[category] = category_count.get(category, 0) + 1
        
        # Calcular tiempo estimado de reparación (minutos)
        time_estimate = (
            severity_count["critical"] * 30 +
            severity_count["high"] * 15 +
            severity_count["medium"] * 5 +
            severity_count["low"] * 2
        )
        
        return {
            "total_issues": len(issues),
            "critical_issues": severity_count["critical"],
            "high_issues": severity_count["high"],
            "medium_issues": severity_count["medium"],
            "low_issues": severity_count["low"],
            "security_issues": category_count.get("security", 0),
            "performance_issues": category_count.get("performance", 0),
            "estimated_time_to_fix": time_estimate
        }

# Singleton para uso global
_ai_engine_instance = None

def get_ai_engine(config: Dict[str, Any] = None) -> SmartFixAIEngine:
    """Obtener instancia singleton del motor de IA"""
    global _ai_engine_instance
    
    if _ai_engine_instance is None and config is not None:
        _ai_engine_instance = SmartFixAIEngine(config)
        _ai_engine_instance.initialize()
    
    return _ai_engine_instance