from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import requests
from config import OPENAI_API_KEY, NEWSAPI_KEY, PROXY_URL  # Импортируем ключи и прокси из config

app = FastAPI()

# Настройка API ключей и прокси
openai.api_key = OPENAI_API_KEY
newsapi_key = NEWSAPI_KEY
proxy_url = PROXY_URL

if not openai.api_key:
    raise ValueError("Переменная OPENAI_API_KEY не установлена")
if not newsapi_key:
    raise ValueError("Переменная NEWSAPI_KEY не установлена")
if not proxy_url:
    raise ValueError("Переменная PROXY_URL не установлена")

# Настройка прокси
proxies = {
    "http": proxy_url,
    "https": proxy_url,
}

class Topic(BaseModel):
    topic: str

def get_recent_news(topic):
    url = f"https://newsapi.org/v2/everything?q={topic}&apiKey={newsapi_key}"
    response = requests.get(url, proxies=proxies)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Ошибка при получении данных из NewsAPI")
    articles = response.json().get("articles", [])
    if not articles:
        return "Свежих новостей не найдено."
    recent_news = [article["title"] for article in articles[:1]]
    return "\n".join(recent_news)

def openai_request(model, messages, max_tokens, temperature):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    response = requests.post(url, headers=headers, json=payload, proxies=proxies)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Ошибка при запросе к OpenAI: {response.text}")
    return response.json()

def generate_post(topic):
    recent_news = get_recent_news(topic)

    # Генерация заголовка
    prompt_title = f"Придумайте привлекательный заголовок для поста на тему: {topic}"
    try:
        response_title = openai_request(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt_title}],
            max_tokens=50,
            temperature=0.7
        )
        title = response_title["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации заголовка: {str(e)}")

    # Генерация мета-описания
    prompt_meta = f"Напишите краткое, но информативное мета-описание для поста с заголовком: {title}"
    try:
        response_meta = openai_request(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt_meta}],
            max_tokens=100,
            temperature=0.7
        )
        meta_description = response_meta["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации мета-описания: {str(e)}")

    # Генерация контента поста
    prompt_post = (
        f"Напишите подробный и увлекательный пост для блога на тему: {topic}, учитывая следующие последние новости:\n"
        f"{recent_news}\n\n"
        "Используйте короткие абзацы, подзаголовки, примеры и ключевые слова для лучшего восприятия и SEO-оптимизации."
    )
    try:
        response_post = openai_request(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt_post}],
            max_tokens=1000,
            temperature=0.7
        )
        post_content = response_post["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации контента поста: {str(e)}")

    return {
        "title": title,
        "meta_description": meta_description,
        "post_content": post_content
    }

@app.post("/generate-post")
async def generate_post_api(topic: Topic):
    generated_post = generate_post(topic.topic)
    return generated_post

@app.get("/heartbeat")
async def heartbeat_api():
    return {"status": "OK"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000)
