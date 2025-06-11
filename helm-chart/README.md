# Meeting Processor Helm Chart

Helm чарт для развертывания Meeting Processor в Kubernetes через ArgoCD.

## Быстрый старт

### 1. Настройка секретов

Обновите значения в `values.yaml`:

```yaml
secrets:
  deepgramApiKey: "your-deepgram-key"
  claudeApiKey: "your-claude-key"
  telegramBotToken: "your-telegram-token"
```

### 2. Настройка домена

```yaml
ingress:
  hosts:
    - host: meeting-processor.your-domain.com
      paths:
        - path: /
          pathType: Prefix
```

### 3. Развертывание через ArgoCD

```bash
# Обновите URL репозитория в argocd-application.yaml
kubectl apply -f helm-chart/argocd-application.yaml
```

### 4. Альтернативное развертывание через Helm

```bash
# Установка
helm install meeting-processor ./helm-chart/meeting-processor

# Обновление
helm upgrade meeting-processor ./helm-chart/meeting-processor

# Удаление
helm uninstall meeting-processor
```

## Конфигурация

### Основные параметры

| Параметр | Описание | Значение по умолчанию |
|----------|----------|----------------------|
| `namespace` | Namespace для развертывания | `meeting-processor` |
| `web.replicaCount` | Количество реплик веб-сервиса | `3` |
| `bot.replicaCount` | Количество реплик бота | `1` |
| `web.image.tag` | Тег Docker образа веб-сервиса | `v1.0.0` |
| `bot.image.tag` | Тег Docker образа бота | `v1.0.0` |

### Ресурсы

```yaml
web:
  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "4Gi"
      cpu: "2000m"

bot:
  resources:
    requests:
      memory: "512Mi"
      cpu: "200m"
    limits:
      memory: "2Gi"
      cpu: "1000m"
```

### Хранилище

```yaml
persistence:
  enabled: true
  storageClass: ""  # Использовать default storage class
  logs:
    size: 5Gi
  webUploads:
    size: 10Gi
  webOutput:
    size: 10Gi
  botTemp:
    size: 5Gi
  botOutput:
    size: 10Gi
```

### Ingress

```yaml
ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: meeting-processor.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: meeting-processor-tls
      hosts:
        - meeting-processor.example.com
```

## Компоненты

### Веб-сервис
- **Порт**: 8000
- **Health checks**: HTTP `/health`
- **Gunicorn**: 6 workers, 4 threads
- **Автомасштабирование**: Поддерживается

### Telegram бот
- **Health checks**: Python exec
- **Автоперезапуск**: Включен
- **Логирование**: В stdout

### Хранилище
- **Логи**: Общие для всех компонентов
- **Загрузки**: Отдельно для веб и бота
- **Вывод**: Отдельно для веб и бота

## Мониторинг

```bash
# Статус подов
kubectl get pods -n meeting-processor

# Логи веб-сервиса
kubectl logs -f deployment/meeting-processor-web -n meeting-processor

# Логи бота
kubectl logs -f deployment/meeting-processor-bot -n meeting-processor

# Health check
kubectl port-forward svc/meeting-processor-web 8000:8000 -n meeting-processor
curl http://localhost:8000/health
```

## Обновление

### Через ArgoCD
1. Обновите тег образа в `values.yaml`
2. ArgoCD автоматически обнаружит изменения
3. Синхронизируйте в ArgoCD UI

### Через Helm
```bash
helm upgrade meeting-processor ./helm-chart/meeting-processor \
  --set web.image.tag=v1.0.1 \
  --set bot.image.tag=v1.0.1
```

## Безопасность

- Контейнеры запускаются от непривилегированного пользователя
- Секреты хранятся в Kubernetes Secret
- SSL/TLS обязателен для production
- Network policies можно добавить дополнительно

## Troubleshooting

### Проблемы с образами
```bash
# Проверка образов
kubectl describe pod <pod-name> -n meeting-processor
```

### Проблемы с хранилищем
```bash
# Проверка PVC
kubectl get pvc -n meeting-processor
kubectl describe pvc <pvc-name> -n meeting-processor
```

### Проблемы с секретами
```bash
# Проверка секретов
kubectl get secret meeting-processor-secrets -n meeting-processor -o yaml
```

## Примеры values.yaml

### Минимальная конфигурация
```yaml
secrets:
  deepgramApiKey: "your-key"
  claudeApiKey: "your-key"
  telegramBotToken: "your-token"

ingress:
  hosts:
    - host: meeting.example.com
```

### Production конфигурация
```yaml
web:
  replicaCount: 5
  resources:
    requests:
      memory: "2Gi"
      cpu: "1000m"
    limits:
      memory: "8Gi"
      cpu: "4000m"

persistence:
  storageClass: "fast-ssd"
  webUploads:
    size: 50Gi
  webOutput:
    size: 100Gi

ingress:
  annotations:
    nginx.ingress.kubernetes.io/rate-limit: "200"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"