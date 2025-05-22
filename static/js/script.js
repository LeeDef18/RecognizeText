document.addEventListener('DOMContentLoaded', function() {
  // Элементы DOM
  const fileInput = document.getElementById('fileInput');
  const preview = document.getElementById('preview');
  const dropZone = document.getElementById('drop-zone');
  const dropPrompt = document.getElementById('dropPrompt');
  const fileNameElem = document.querySelector('.filename');
  const buttonsBg = document.getElementById('buttonsBg');
  const deleteBtn = document.querySelector('.delete-btn');
  const refreshBtn = document.querySelector('.refresh-btn');
  const recognizeBtn = document.getElementById('recognizeBtn');
  const output = document.getElementById('output');
  const outputText = document.getElementById('outputText');
  const recognizedText = document.getElementById('recognizedText');
  const copyBtn = document.getElementById('copyBtn');
  const likeBtn = document.getElementById('likeBtn');
  const reprocessBtn = document.getElementById('reprocessBtn');
  const procentElem = document.querySelector('.procent');
  const detectElem = document.querySelector('.detect');

  // Конфигурация
  const CONFIG = {
    API_ENDPOINT: '/upload',
    MAX_FILENAME_LENGTH: 30,
    ALLOWED_TYPES: ['image/jpeg', 'image/png', 'image/jpg']
  };

  // Состояние приложения
  let recognitionInProgress = false;
  let currentResultId = null;

  // Функция для отображения системных сообщений
  function showSystemMessage(message, type = 'error', duration = 5000) {
    const messageBox = document.createElement('div');
    messageBox.className = `system-message ${type}`;
    messageBox.innerHTML = `
      <div class="message-content">
        ${message}
        <button class="close-btn">×</button>
      </div>
    `;

    document.body.appendChild(messageBox);

    messageBox.querySelector('.close-btn').addEventListener('click', () => {
      messageBox.remove();
    });

    if (type !== 'error' && duration > 0) {
      setTimeout(() => messageBox.remove(), duration);
    }
  }

  // Обработка выбора файла
  function handleFileSelect() {
    const file = fileInput.files[0];

    // Проверка типа файла
    if (!CONFIG.ALLOWED_TYPES.includes(file.type)) {
      showSystemMessage('Неподдерживаемый формат файла', 'error');
      resetFileInput();
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      preview.src = e.target.result;
      preview.style.display = 'block';
      dropPrompt.style.display = 'none';
      fileNameElem.textContent = truncateFileName(file.name, CONFIG.MAX_FILENAME_LENGTH);
      buttonsBg.style.display = 'flex';
      dropZone.classList.add('no-border');
      recognizeBtn.classList.remove('disabled');
      resetOutput();
    };
    reader.readAsDataURL(file);
  }

  // Сброс состояния файлового ввода
  function resetFileInput() {
    preview.src = '';
    preview.style.display = 'none';
    fileInput.value = '';
    fileNameElem.textContent = '';
    buttonsBg.style.display = 'none';
    dropPrompt.style.display = 'block';
    dropZone.classList.remove('no-border');
    resetOutput();
    likeBtn.classList.remove('liked');
  }

  // Сброс результатов распознавания
  function resetOutput() {
    output.style.display = 'none';
    outputText.style.display = 'none';
    outputText.classList.remove('visible');
    recognizedText.textContent = '';
    currentResultId = null;
  }

  // Обрезание длинных имен файлов
  function truncateFileName(name, maxLength) {
    if (name.length <= maxLength) return name;
    const extension = name.split('.').pop();
    const basename = name.substring(0, name.length - extension.length - 1);
    const truncated = basename.substring(0, maxLength - extension.length - 3) + '...';
    return truncated + '.' + extension;
  }

  // Функция распознавания текста
  async function startRecognition() {
    if (!fileInput.files[0]) {
      showSystemMessage('Выберите изображение', 'warning');
      return;
    }

    if (recognitionInProgress) {
      showSystemMessage('Дождитесь завершения текущего распознавания', 'warning');
      return;
    }

    recognitionInProgress = true;
    recognizeBtn.disabled = true;
    output.style.display = 'flex';
    detectElem.textContent = "Распознаем...";
    procentElem.textContent = "0%";

    try {
      const formData = new FormData();
      formData.append('file', fileInput.files[0]);

      // Отправка на сервер Flask
      const response = await fetch(CONFIG.API_ENDPOINT, {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (result.error) {
        throw new Error(result.error);
      }

      currentResultId = result.id;
      showRecognitionResult(result.text);
    } catch (error) {
      console.error('Ошибка распознавания:', error);
      showSystemMessage(`Ошибка распознавания: ${error.message}`, 'error');
    } finally {
      recognitionInProgress = false;
      recognizeBtn.disabled = false;
    }
  }

  // Отображение результата распознавания
  function showRecognitionResult(text) {
    output.classList.add('fade-out');
    setTimeout(() => {
      output.style.display = 'none';
      output.classList.remove('fade-out');
      recognizedText.textContent = text;
      outputText.style.display = 'block';
      setTimeout(() => outputText.classList.add('visible'), 10);
    }, 500);
  }

  // Копирование текста
  function copyText() {
    if (!recognizedText.textContent.trim()) return;

    navigator.clipboard.writeText(recognizedText.textContent)
      .then(() => {
        const copyText = copyBtn.querySelector('.reply-text');
        const originalText = copyText.textContent;
        copyText.textContent = 'Скопировано!';
        setTimeout(() => copyText.textContent = originalText, 2000);
      })
      .catch(err => {
        console.error('Copy failed:', err);
        showSystemMessage('Ошибка копирования', 'error');
      });
  }

  // Лайк результата
  function toggleLike() {
    likeBtn.classList.toggle('liked');

    // Здесь можно добавить сохранение лайка в базу данных
    if (currentResultId && likeBtn.classList.contains('liked')) {
      // fetch(`/like/${currentResultId}`, { method: 'POST' })
    }
  }

  // Повторная обработка
  function reprocessText() {
    outputText.classList.remove('visible');
    setTimeout(() => {
      outputText.style.display = 'none';
      startRecognition();
    }, 300);
  }

  // Drag and Drop обработчики
  function handleDragOver(e) {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  }

  function handleDragLeave() {
    dropZone.classList.remove('drag-over');
  }

  function handleDrop(e) {
    e.preventDefault();
    dropZone.classList.remove('drag-over');

    if (e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
      handleFileSelect();
    }
  }

  // Инициализация приложения
  function initializeApp() {
    showSystemMessage('Система готова к работе', 'success', 3000);
  }

  // Назначение обработчиков событий
  fileInput.addEventListener('change', handleFileSelect);
  dropZone.addEventListener('click', (e) => {
    if (e.target === dropZone || e.target.classList.contains('drop-zone__main-text')) {
      fileInput.click();
    }
  });

  deleteBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    resetFileInput();
  });

  refreshBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  recognizeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    startRecognition();
  });

  copyBtn.addEventListener('click', copyText);
  likeBtn.addEventListener('click', toggleLike);
  reprocessBtn.addEventListener('click', reprocessText);

  dropZone.addEventListener('dragover', handleDragOver);
  dropZone.addEventListener('dragleave', handleDragLeave);
  dropZone.addEventListener('drop', handleDrop);

  // Инициализация приложения
  initializeApp();
});