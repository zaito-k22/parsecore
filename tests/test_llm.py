from app.services.llm.service import llm_service

respuesta = llm_service.chat(
    "Di únicamente la palabra 'Hola'."
)

print(respuesta)