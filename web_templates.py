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
            <div class="navbar-nav d-flex flex-row">
                <a class="nav-link me-3" href="/docs"><i class="fas fa-book me-1"></i>Документация</a>
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
    
    def get_docs_index_template(self):
        """Возвращает HTML шаблон главной страницы документации"""
        return '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Документация - Meeting Processor</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/"><i class="fas fa-microphone me-2"></i>Meeting Processor</a>
            <div class="navbar-nav">
                <a class="nav-link" href="/"><i class="fas fa-home me-1"></i>Главная</a>
                <a class="nav-link" href="/jobs"><i class="fas fa-list me-1"></i>Все задачи</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row">
            <div class="col-12">
                <div class="card shadow mb-4">
                    <div class="card-header bg-info text-white">
                        <h3><i class="fas fa-book me-2"></i>Документация по проведению встреч</h3>
                        <p class="mb-0">Руководства для получения качественных протоколов с помощью автоматической транскрибации</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-4 mb-4">
                <div class="card h-100 shadow-sm">
                    <div class="card-body">
                        <div class="text-center mb-3">
                            <i class="fas fa-tasks fa-3x text-success"></i>
                        </div>
                        <h5 class="card-title text-center">Быстрый чек-лист</h5>
                        <p class="card-text">Краткий справочник для ежедневного использования: проверка перед встречей, правила во время встречи.</p>
                        <div class="text-center">
                            <a href="/docs/checklist" target="_blank" class="btn btn-success">
                                <i class="fas fa-external-link-alt me-2"></i>Открыть
                            </a>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-md-4 mb-4">
                <div class="card h-100 shadow-sm">
                    <div class="card-body">
                        <div class="text-center mb-3">
                            <i class="fas fa-file-alt fa-3x text-info"></i>
                        </div>
                        <h5 class="card-title text-center">Полное руководство</h5>
                        <p class="card-text">Детальные рекомендации по всем аспектам: техническая подготовка, правила речи, примеры практики.</p>
                        <div class="text-center">
                            <a href="/docs/guidelines" target="_blank" class="btn btn-info">
                                <i class="fas fa-external-link-alt me-2"></i>Открыть
                            </a>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-md-4 mb-4">
                <div class="card h-100 shadow-sm">
                    <div class="card-body">
                        <div class="text-center mb-3">
                            <i class="fas fa-cogs fa-3x text-warning"></i>
                        </div>
                        <h5 class="card-title text-center">Техническое руководство</h5>
                        <p class="card-text">Подробные инструкции по настройке записи для Zoom, Google Meet, KTalk и проприетарного ПО.</p>
                        <div class="text-center">
                            <a href="/docs/setup" target="_blank" class="btn btn-warning">
                                <i class="fas fa-external-link-alt me-2"></i>Открыть
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mt-4">
            <div class="col-12">
                <div class="card border-primary">
                    <div class="card-header bg-primary text-white">
                        <h5><i class="fas fa-lightbulb me-2"></i>Ключевые принципы</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-4">
                                <h6><i class="fas fa-microphone text-primary me-2"></i>Главное правило</h6>
                                <p class="small">Представление участников в начале встречи - КРИТИЧНО!</p>
                            </div>
                            <div class="col-md-4">
                                <h6><i class="fas fa-comments text-success me-2"></i>Правила речи</h6>
                                <p class="small">Четко говорить, делать паузы, называть себя при выступлении</p>
                            </div>
                            <div class="col-md-4">
                                <h6><i class="fas fa-file-audio text-info me-2"></i>Техническая основа</h6>
                                <p class="small">MP3, WAV, M4A, AAC (до 25МБ), 256 kbps, 44.1 kHz</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mt-4">
            <div class="col-12">
                <div class="alert alert-info">
                    <h6><i class="fas fa-info-circle me-2"></i>Как использовать документацию</h6>
                    <ul class="mb-0">
                        <li><strong>Новичкам:</strong> Начните с быстрого чек-листа, затем изучите полное руководство</li>
                        <li><strong>Опытным пользователям:</strong> Используйте техническое руководство для настройки</li>
                        <li><strong>Для справки:</strong> Обзор документации содержит все ключевые моменты</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
        '''
    
    def get_docs_view_template(self):
        """Возвращает HTML шаблон для просмотра документации"""
        return '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ doc_title }} - Meeting Processor</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        .markdown-content {
            line-height: 1.7;
            font-size: 16px;
        }
        .markdown-content h1 {
            color: #0d6efd;
            border-bottom: 3px solid #0d6efd;
            padding-bottom: 0.5rem;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        .markdown-content h2 {
            color: #198754;
            border-bottom: 2px solid #198754;
            padding-bottom: 0.3rem;
            margin-top: 1.5rem;
            margin-bottom: 0.8rem;
        }
        .markdown-content h3 {
            color: #fd7e14;
            margin-top: 1.2rem;
            margin-bottom: 0.6rem;
        }
        .markdown-content h4 {
            color: #6f42c1;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }
        .markdown-content ul, .markdown-content ol {
            margin-bottom: 1rem;
            padding-left: 1.5rem;
        }
        .markdown-content li {
            margin-bottom: 0.3rem;
        }
        .markdown-content code {
            background-color: #f8f9fa;
            padding: 0.2rem 0.4rem;
            border-radius: 0.25rem;
            font-size: 0.9em;
            color: #d63384;
        }
        .markdown-content pre {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #0d6efd;
            overflow-x: auto;
        }
        .markdown-content pre code {
            background: none;
            padding: 0;
            color: inherit;
        }
        .markdown-content blockquote {
            border-left: 4px solid #0d6efd;
            padding-left: 1rem;
            margin: 1rem 0;
            background-color: #f8f9fa;
            padding: 0.8rem 1rem;
            border-radius: 0.25rem;
        }
        .markdown-content table {
            width: 100%;
            margin-bottom: 1rem;
            border-collapse: collapse;
        }
        .markdown-content table th,
        .markdown-content table td {
            padding: 0.75rem;
            border: 1px solid #dee2e6;
        }
        .markdown-content table th {
            background-color: #e9ecef;
            font-weight: bold;
        }
        .markdown-content table tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        .markdown-content .emoji {
            font-size: 1.2em;
        }
        .toc {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 2rem;
        }
        .toc ul {
            margin-bottom: 0;
        }
        .toc a {
            text-decoration: none;
            color: #0d6efd;
        }
        .toc a:hover {
            text-decoration: underline;
        }
        .back-to-top {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
        }
    </style>
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-primary sticky-top">
        <div class="container">
            <a class="navbar-brand" href="/"><i class="fas fa-microphone me-2"></i>Meeting Processor</a>
            <div class="navbar-nav d-flex flex-row">
                <a class="nav-link me-3" href="/docs"><i class="fas fa-arrow-left me-1"></i>К документации</a>
                <a class="nav-link me-3" href="/"><i class="fas fa-home me-1"></i>Главная</a>
                <a class="nav-link" href="/jobs"><i class="fas fa-list me-1"></i>Задачи</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="card shadow">
            <div class="card-header bg-info text-white d-flex justify-content-between align-items-center">
                <h4><i class="fas fa-book me-2"></i>{{ doc_title }}</h4>
                <div>
                    <button onclick="window.print()" class="btn btn-light btn-sm me-2">
                        <i class="fas fa-print me-1"></i>Печать
                    </button>
                    <button onclick="toggleToc()" class="btn btn-outline-light btn-sm">
                        <i class="fas fa-list me-1"></i>Содержание
                    </button>
                </div>
            </div>
            <div class="card-body">
                <!-- Содержание (скрыто по умолчанию) -->
                <div id="toc" class="toc" style="display: none;">
                    <h6><i class="fas fa-list me-2"></i>Содержание</h6>
                    <div id="toc-content"></div>
                </div>
                
                <!-- Основной контент -->
                <div id="markdown-content" class="markdown-content"></div>
            </div>
        </div>
    </div>

    <!-- Кнопка "Наверх" -->
    <button onclick="scrollToTop()" class="btn btn-primary back-to-top" title="Наверх">
        <i class="fas fa-arrow-up"></i>
    </button>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Загружаем и отображаем markdown контент
        const markdownText = {{ content|tojson }};
        const contentDiv = document.getElementById('markdown-content');
        
        // Настраиваем marked для поддержки эмодзи
        marked.setOptions({
            breaks: true,
            gfm: true
        });
        
        // Конвертируем markdown в HTML
        contentDiv.innerHTML = marked.parse(markdownText);
        
        // Генерируем содержание
        generateToc();
        
        // Добавляем якоря к заголовкам
        addAnchorsToHeadings();
        
        function generateToc() {
            const headings = contentDiv.querySelectorAll('h1, h2, h3, h4');
            const tocContent = document.getElementById('toc-content');
            
            if (headings.length === 0) {
                document.getElementById('toc').style.display = 'none';
                return;
            }
            
            let tocHtml = '<ul>';
            headings.forEach((heading, index) => {
                const id = 'heading-' + index;
                heading.id = id;
                const level = parseInt(heading.tagName.charAt(1));
                const indent = 'ms-' + ((level - 1) * 3);
                tocHtml += `<li class="${indent}"><a href="#${id}">${heading.textContent}</a></li>`;
            });
            tocHtml += '</ul>';
            
            tocContent.innerHTML = tocHtml;
        }
        
        function addAnchorsToHeadings() {
            const headings = contentDiv.querySelectorAll('h1, h2, h3, h4');
            headings.forEach(heading => {
                heading.style.cursor = 'pointer';
                heading.title = 'Нажмите, чтобы скопировать ссылку';
                heading.addEventListener('click', function() {
                    const url = window.location.origin + window.location.pathname + '#' + this.id;
                    navigator.clipboard.writeText(url).then(() => {
                        // Показываем уведомление
                        const toast = document.createElement('div');
                        toast.className = 'alert alert-success position-fixed';
                        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; opacity: 0.9;';
                        toast.innerHTML = '<i class="fas fa-check me-2"></i>Ссылка скопирована!';
                        document.body.appendChild(toast);
                        setTimeout(() => toast.remove(), 2000);
                    });
                });
            });
        }
        
        function toggleToc() {
            const toc = document.getElementById('toc');
            toc.style.display = toc.style.display === 'none' ? 'block' : 'none';
        }
        
        function scrollToTop() {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
        
        // Показываем/скрываем кнопку "Наверх"
        window.addEventListener('scroll', function() {
            const backToTop = document.querySelector('.back-to-top');
            if (window.pageYOffset > 300) {
                backToTop.style.display = 'block';
            } else {
                backToTop.style.display = 'none';
            }
        });
        
        // Плавная прокрутка для якорных ссылок
        document.addEventListener('click', function(e) {
            if (e.target.tagName === 'A' && e.target.getAttribute('href').startsWith('#')) {
                e.preventDefault();
                const targetId = e.target.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);
                if (targetElement) {
                    targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        });
    </script>
</body>
</html>
        '''
