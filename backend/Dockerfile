FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]