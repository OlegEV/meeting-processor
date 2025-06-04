"""
HTML шаблоны для веб-приложения Meeting Processor
"""

class WebTemplates:
    """Класс для хранения HTML шаблонов веб-приложения"""
    
    def get_index_template(self):
        """Возвращает HTML шаблон главной страницы"""
        return '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meeting Processor</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-primary">
        <div class="container">
            <span class="navbar-brand"><i class="fas fa-microphone me-2"></i>Meeting Processor</span>
            <div class="navbar-nav">
                <a class="nav-link" href="/jobs"><i class="fas fa-list me-1"></i>Все задачи</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else 'success' }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card shadow">
                    <div class="card-header bg-primary text-white">
                        <h4><i class="fas fa-upload me-2"></i>Загрузка файла для обработки</h4>
                    </div>
                    <div class="card-body">
                        <form id="uploadForm" method="POST" action="/upload" enctype="multipart/form-data">
                            <div class="mb-3">
                                <label for="template" class="form-label">Шаблон протокола:</label>
                                <select class="form-select" name="template" required>
                                    {% for template_id, description in templates.items() %}
                                        <option value="{{ template_id }}" {% if template_id == 'standard' %}selected{% endif %}>
                                            {{ template_id.title() }} - {{ description }}
                                        </option>
                                    {% endfor %}
                                </select>
                            </div>

                            <div class="mb-3">
                                <label for="file" class="form-label">Выберите файл:</label>
                                <input type="file" class="form-control" id="fileInput" name="file" accept="{{ accept_string }}" required>
                                <div class="form-text">
                                    Максимальный размер: {{ max_size_mb }} МБ<br>
                                    Поддерживаемые форматы: {{ formats_display }}
                                </div>
                            </div>

                            <!-- Прогресс бар загрузки (скрыт по умолчанию) -->
                            <div id="uploadProgress" class="mb-3" style="display: none;">
                                <div class="progress" style="height: 25px;">
                                    <div id="uploadProgressBar" class="progress-bar progress-bar-striped progress-bar-animated" 
                                         style="width: 0%;">
                                        <span id="uploadProgressText">0%</span>
                                    </div>
                                </div>
                                <small class="text-muted mt-1 d-block">Загрузка файла на сервер...</small>
                            </div>

                            <button type="submit" id="submitBtn" class="btn btn-success btn-lg w-100">
                                <i class="fas fa-rocket me-2"></i>Начать обработку
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mt-5">
            <div class="col-md-4">
                <div class="card h-100">
                    <div class="card-body text-center">
                        <i class="fas fa-microphone fa-3x text-primary mb-3"></i>
                        <h5>Транскрипция</h5>
                        <p class="text-muted">Автоматическое преобразование речи в текст</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card h-100">
                    <div class="card-body text-center">
                        <i class="fas fa-file-alt fa-3x text-success mb-3"></i>
                        <h5>Протоколы</h5>
                        <p class="text-muted">Структурированные протоколы встреч</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card h-100">
                    <div class="card-body text-center">
                        <i class="fas fa-users fa-3x text-info mb-3"></i>
                        <h5>Участники</h5>
                        <p class="text-muted">Автоматическая идентификация спикеров</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.getElementById('uploadForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const fileInput = document.getElementById('fileInput');
            const uploadProgress = document.getElementById('uploadProgress');
            const uploadProgressBar = document.getElementById('uploadProgressBar');
            const uploadProgressText = document.getElementById('uploadProgressText');
            const submitBtn = document.getElementById('submitBtn');
            
            // Проверяем, выбран ли файл
            if (!fileInput.files[0]) {
                alert('Пожалуйста, выберите файл');
                return;
            }
            
            // Показываем прогресс бар и блокируем кнопку
            uploadProgress.style.display = 'block';
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Загрузка...';
            
            // Создаем XMLHttpRequest для отслеживания прогресса
            const xhr = new XMLHttpRequest();
            
            // Отслеживание прогресса загрузки
            xhr.upload.addEventListener('progress', function(e) {
                if (e.lengthComputable) {
                    const percentComplete = Math.round((e.loaded / e.total) * 100);
                    uploadProgressBar.style.width = percentComplete + '%';
                    uploadProgressText.textContent = percentComplete + '%';
                }
            });
            
            // Обработка завершения загрузки
            xhr.addEventListener('load', function() {
                if (xhr.status === 200) {
                    // Успешная загрузка - перенаправляем
                    window.location.href = xhr.responseURL;
                } else {
                    // Ошибка загрузки
                    alert('Ошибка загрузки файла');
                    uploadProgress.style.display = 'none';
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-rocket me-2"></i>Начать обработку';
                }
            });
            
            // Обработка ошибок
            xhr.addEventListener('error', function() {
                alert('Ошибка сети при загрузке файла');
                uploadProgress.style.display = 'none';
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-rocket me-2"></i>Начать обработку';
            });
            
            // Отправляем файл
            xhr.open('POST', '/upload');
            xhr.send(formData);
        });
    </script>
</body>
</html>
        '''
    
    def get_status_template(self):
        """Возвращает HTML шаблон страницы статуса"""
        return '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Статус обработки</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/"><i class="fas fa-microphone me-2"></i>Meeting Processor</a>
            <div class="navbar-nav">
                <a class="nav-link" href="/jobs"><i class="fas fa-list me-1"></i>Все задачи</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card shadow">
                    <div class="card-header bg-primary text-white">
                        <h4><i class="fas fa-tasks me-2"></i>Статус обработки</h4>
                    </div>
                    <div class="card-body text-center">
                        <div class="mb-3">
                            {% if job.status == 'completed' %}
                                <i class="fas fa-check-circle fa-4x text-success"></i>
                            {% elif job.status == 'error' %}
                                <i class="fas fa-exclamation-circle fa-4x text-danger"></i>
                            {% else %}
                                <i class="fas fa-cog fa-spin fa-4x text-primary"></i>
                            {% endif %}
                        </div>

                        <h5>{{ job.filename }}</h5>
                        <p class="text-muted">Шаблон: {{ job.template }}</p>

                        <div class="progress mb-3" style="height: 30px;">
                            <div class="progress-bar 
                                {% if job.status == 'completed' %}bg-success{% elif job.status == 'error' %}bg-danger{% else %}bg-primary progress-bar-animated{% endif %}" 
                                style="width: {{ job.progress }}%">
                                {{ job.progress }}%
                            </div>
                        </div>

                        <div class="alert 
                            {% if job.status == 'completed' %}alert-success{% elif job.status == 'error' %}alert-danger{% else %}alert-info{% endif %}">
                            {{ job.message }}
                        </div>

                        {% if job.status == 'completed' %}
                            <div class="row mb-3">
                                <div class="col-md-6">
                                    <a href="/view/{{ job_id }}/transcript" class="btn btn-outline-info w-100 mb-2">
                                        <i class="fas fa-eye me-2"></i>Просмотреть транскрипт
                                    </a>
                                </div>
                                <div class="col-md-6">
                                    <a href="/view/{{ job_id }}/summary" class="btn btn-info w-100 mb-2">
                                        <i class="fas fa-eye me-2"></i>Просмотреть протокол
                                    </a>
                                </div>
                            </div>
                            <div class="row mb-3">
                                <div class="col-md-6">
                                    <a href="/download/{{ job_id }}/transcript" class="btn btn-outline-primary w-100 mb-2">
                                        <i class="fas fa-file-alt me-2"></i>Скачать транскрипт
                                    </a>
                                </div>
                                <div class="col-md-6">
                                    <a href="/download/{{ job_id }}/summary" class="btn btn-primary w-100 mb-2">
                                        <i class="fas fa-file-download me-2"></i>Скачать протокол
                                    </a>
                                </div>
                            </div>
                            
                            <!-- Форма для генерации протокола в новом шаблоне -->
                            <div class="card border-warning mb-3">
                                <div class="card-header bg-warning text-dark">
                                    <h6 class="mb-0"><i class="fas fa-magic me-2"></i>Сгенерировать протокол в другом шаблоне</h6>
                                </div>
                                <div class="card-body">
                                    <form method="POST" action="/generate_protocol/{{ job_id }}">
                                        <div class="row align-items-end">
                                            <div class="col-md-8">
                                                <label for="new_template" class="form-label">Выберите новый шаблон:</label>
                                                <select class="form-select" name="new_template" required>
                                                    {% for template_id, description in templates.items() %}
                                                        {% if template_id != job.template %}
                                                            <option value="{{ template_id }}">
                                                                {{ template_id.title() }} - {{ description }}
                                                            </option>
                                                        {% endif %}
                                                    {% endfor %}
                                                </select>
                                            </div>
                                            <div class="col-md-4">
                                                <button type="submit" class="btn btn-warning w-100">
                                                    <i class="fas fa-cogs me-2"></i>Сгенерировать
                                                </button>
                                            </div>
                                        </div>
                                        <div class="form-text mt-2">
                                            <i class="fas fa-info-circle me-1"></i>
                                            Будет создан новый протокол на основе существующего транскрипта
                                        </div>
                                    </form>
                                </div>
                            </div>
                            
                            <a href="/" class="btn btn-success">
                                <i class="fas fa-plus me-2"></i>Обработать еще файл
                            </a>
                        {% elif job.status == 'error' %}
                            <a href="/" class="btn btn-primary">
                                <i class="fas fa-upload me-2"></i>Попробовать снова
                            </a>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        {% if job.status not in ['completed', 'error'] %}
            setInterval(function() {
                fetch('/api/status/{{ job_id }}')
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'completed' || data.status === 'error') {
                            location.reload();
                        } else {
                            const progressBar = document.querySelector('.progress-bar');
                            const alertDiv = document.querySelector('.alert');
                            
                            progressBar.style.width = data.progress + '%';
                            progressBar.textContent = data.progress + '%';
                            alertDiv.textContent = data.message;
                        }
                    })
                    .catch(error => console.error('Ошибка обновления статуса:', error));
            }, 2000);
        {% endif %}
    </script>
</body>
</html>
        '''
    
    def get_view_template(self):
        """Возвращает HTML шаблон для просмотра файлов"""
        return '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ file_title }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    {% if is_markdown %}
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        .markdown-content {
            line-height: 1.6;
        }
        .markdown-content h1, .markdown-content h2, .markdown-content h3 {
            color: #0d6efd;
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
        }
        .markdown-content ul, .markdown-content ol {
            margin-bottom: 1rem;
        }
        .markdown-content li {
            margin-bottom: 0.25rem;
        }
        .markdown-content code {
            background-color: #f8f9fa;
            padding: 0.125rem 0.25rem;
            border-radius: 0.25rem;
        }
        .markdown-content blockquote {
            border-left: 4px solid #0d6efd;
            padding-left: 1rem;
            margin: 1rem 0;
            background-color: #f8f9fa;
            padding: 0.5rem 1rem;
        }
    </style>
    {% endif %}
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/"><i class="fas fa-microphone me-2"></i>Meeting Processor</a>
            <div class="navbar-nav">
                <a class="nav-link" href="/jobs"><i class="fas fa-list me-1"></i>Все задачи</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="card shadow">
            <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                <h4><i class="fas fa-file-alt me-2"></i>{{ file_title }}</h4>
                <div>
                    <a href="/download/{{ job_id }}/{{ file_type }}" class="btn btn-light btn-sm me-2">
                        <i class="fas fa-download me-1"></i>Скачать
                    </a>
                    <a href="/status/{{ job_id }}" class="btn btn-outline-light btn-sm">
                        <i class="fas fa-arrow-left me-1"></i>Назад
                    </a>
                </div>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <small class="text-muted">
                        <i class="fas fa-file me-1"></i>Файл: {{ filename }}
                    </small>
                </div>
                
                {% if is_markdown %}
                    <div id="markdown-content" class="markdown-content"></div>
                    <script>
                        const markdownText = {{ content|tojson }};
                        document.getElementById('markdown-content').innerHTML = marked.parse(markdownText);
                    </script>
                {% else %}
                    <pre class="bg-light p-3 rounded" style="white-space: pre-wrap; max-height: 70vh; overflow-y: auto;">{{ content }}</pre>
                {% endif %}
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
        '''
    
    def get_jobs_template(self):
        """Возвращает HTML шаблон списка задач"""
        return '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Все задачи</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/"><i class="fas fa-microphone me-2"></i>Meeting Processor</a>
            <div class="navbar-nav">
                <a class="nav-link" href="/"><i class="fas fa-upload me-1"></i>Загрузить файл</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="card shadow">
            <div class="card-header bg-primary text-white">
                <h4><i class="fas fa-list me-2"></i>История обработки файлов</h4>
            </div>
            <div class="card-body">
                {% if jobs %}
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead class="table-light">
                                <tr>
                                    <th>Файл</th>
                                    <th>Шаблон</th>
                                    <th>Статус</th>
                                    <th>Прогресс</th>
                                    <th>Дата создания</th>
                                    <th>Действия</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for job in jobs %}
                                    <tr>
                                        <td><i class="fas fa-file me-1"></i>{{ job.filename }}</td>
                                        <td><span class="badge bg-secondary">{{ job.template }}</span></td>
                                        <td>
                                            {% if job.status == 'completed' %}
                                                <span class="badge bg-success"><i class="fas fa-check me-1"></i>Завершено</span>
                                            {% elif job.status == 'error' %}
                                                <span class="badge bg-danger"><i class="fas fa-exclamation me-1"></i>Ошибка</span>
                                            {% elif job.status == 'processing' %}
                                                <span class="badge bg-primary"><i class="fas fa-cog fa-spin me-1"></i>Обработка</span>
                                            {% else %}
                                                <span class="badge bg-warning"><i class="fas fa-clock me-1"></i>Ожидание</span>
                                            {% endif %}
                                        </td>
                                        <td>
                                            <div class="progress" style="height: 20px; width: 100px;">
                                                <div class="progress-bar {% if job.status == 'completed' %}bg-success{% elif job.status == 'error' %}bg-danger{% else %}bg-primary{% endif %}" 
                                                    style="width: {{ job.progress }}%">
                                                    <small>{{ job.progress }}%</small>
                                                </div>
                                            </div>
                                        </td>
                                        <td>{{ job.created_at }}</td>
                                        <td>
                                            <a href="/status/{{ job.id }}" class="btn btn-sm btn-outline-primary">
                                                <i class="fas fa-eye me-1"></i>Подробнее
                                            </a>
                                        </td>
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                {% else %}
                    <div class="text-center py-5">
                        <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
                        <h5 class="text-muted">Нет обработанных файлов</h5>
                        <p class="text-muted">Загрузите первый файл для начала работы</p>
                        <a href="/" class="btn btn-primary">
                            <i class="fas fa-upload me-2"></i>Загрузить файл
                        </a>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
        '''