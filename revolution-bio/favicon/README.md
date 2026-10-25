# Фавиконы Революшн Био

Эмблема логотипа (сфера-сеть) на графитовом фоне сайта `#2b3035`. Для маленьких размеров
(16–48 px) линии утолщены, чтобы значок читался во вкладке браузера.

| Файл | Где используется |
|---|---|
| `favicon.ico` | Вкладка браузера, закладки (внутри 16, 32 и 48 px) |
| `favicon.svg` | Векторная иконка для современных браузеров |
| `favicon-16x16.png`, `-32x32`, `-48x48`, `-96x96` | PNG-версии для вкладок и поиска (Яндекс берёт от 120 px — см. ниже) |
| `apple-touch-icon.png` (180 px), `apple-touch-icon-152x152.png` | Иконка на экране iPhone/iPad |
| `android-chrome-192x192.png`, `-512x512.png`, `maskable-512x512.png` | Android, ярлык на рабочем столе |
| `mstile-150x150.png` | Плитка Windows |
| `safari-pinned-tab.svg` | Закреплённая вкладка Safari (одноцветная) |
| `site.webmanifest` | Манифест для Android (для своего хостинга; в Tilda не нужен) |

## Как поставить в Tilda
1. **Настройки сайта → Ещё → Иконка для сайта (favicon)** — загрузите `favicon.ico`
   (если Tilda попросит PNG — `favicon-96x96.png`).
2. Там же **иконка для мобильных устройств** — загрузите `apple-touch-icon.png` (180×180)
   или `apple-touch-icon-152x152.png`, если Tilda просит 152×152.
3. Необязательно, для чёткой иконки в новых браузерах: **Настройки сайта → Ещё →
   HTML-код для вставки внутрь head** — вставьте:

```html
<link rel="icon" type="image/svg+xml" href="https://cdn.jsdelivr.net/gh/freyia-me/calyra-assets@f9a39ab52285/revolution-bio/favicon/favicon.svg">
<link rel="icon" type="image/png" sizes="96x96" href="https://cdn.jsdelivr.net/gh/freyia-me/calyra-assets@f9a39ab52285/revolution-bio/favicon/favicon-96x96.png">
<link rel="mask-icon" href="https://cdn.jsdelivr.net/gh/freyia-me/calyra-assets@f9a39ab52285/revolution-bio/favicon/safari-pinned-tab.svg" color="#36cbe0">
<meta name="theme-color" content="#2b3035">
```

4. Опубликуйте все страницы. Браузеры долго хранят старый значок — проверяйте в окне инкогнито.
