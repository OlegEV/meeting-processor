# Сторонние компоненты веб-интерфейса

Библиотеки и шрифты лежат в репозитории и раздаются самим приложением (`/static/vendor/...`).
Страницы не обращаются к внешним CDN, поэтому интерфейс работает в сети без доступа в интернет.

| Компонент | Версия | Файлы | Лицензия |
|---|---|---|---|
| Bootstrap | 5.1.3 | `bootstrap/css/bootstrap.min.css`, `bootstrap/js/bootstrap.bundle.min.js` | MIT |
| Font Awesome Free | 6.0.0 | `fontawesome/css/all.min.css`, `fontawesome/webfonts/*` | иконки — CC BY 4.0, шрифты — SIL OFL 1.1, код — MIT |
| marked | 15.0.12 | `marked/marked.min.js` | MIT |
| Chart.js | 4.6.1 | `chartjs/chart.umd.min.js` | MIT |

Файлы взяты из npm-пакетов `bootstrap`, `@fortawesome/fontawesome-free`, `marked`, `chart.js` без изменений.
Чтобы обновить компонент, замените файлы на соответствующие из новой версии пакета и поправьте таблицу.
`fontawesome/css/all.min.css` ссылается на шрифты по относительному пути `../webfonts/`, поэтому структуру каталогов менять нельзя.
