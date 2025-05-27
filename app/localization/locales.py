"""
Localization service for managing multi-language text resources.
Provides centralized access to translated strings.
"""

import logging
from typing import Dict, Optional, Any # Added Any for TEXTS structure hint

logger = logging.getLogger(__name__)

# Define language names for selection keyboards
LANGUAGE_NAMES = {
    "en": {"en": "English", "ru": "Английский", "pl": "Angielski"},
    "ru": {"en": "Russian", "ru": "Русский", "pl": "Rosyjski"},
    "pl": {"en": "Polish", "ru": "Польский", "pl": "Polski"},
}

TEXTS: Dict[str, Dict[Optional[str], str]] = { # Allow Optional[str] for language keys if one might be None
    # Language Names (used for language selection keyboard)
    "language_name_en": LANGUAGE_NAMES["en"],
    "language_name_ru": LANGUAGE_NAMES["ru"],
    "language_name_pl": LANGUAGE_NAMES["pl"],

    # Common texts
    "welcome_back": {"en": "👋 Welcome back, {username}!", "ru": "👋 С возвращением, {username}!", "pl": "👋 Witamy ponownie, {username}!"},
    "language_selected": {"en": "✅ Language set!", "ru": "✅ Язык установлен!", "pl": "✅ Język ustawiony!"},
    "language_saved": {"en": "Language saved!", "ru": "Язык сохранён!", "pl": "Język zapisany!"},
    "main_menu": {"en": "🛍 Main Menu\nWhat would you like to do?", "ru": "🛍 Главное меню\nЧто вы хотите сделать?", "pl": "🛍 Menu główne\nCo chciałbyś zrobić?"},
    "main_menu_button": {"en": "🏠 Main Menu", "ru": "🏠 Главное меню", "pl": "🏠 Menu główne"},
    "choose_language": {"en": "🌍 Please choose your language:", "ru": "🌍 Пожалуйста, выберите ваш язык:", "pl": "🌍 Proszę wybrać swój język:"},
    "choose_language_initial": {"en": "🌍 Welcome! Please choose your language / Добро пожаловать! Выберите ваш язык / Witamy! Wybierz swój język", "ru": "🌍 Welcome! Please choose your language / Добро пожаловать! Выберите ваш язык / Witamy! Wybierz swój język", "pl": "🌍 Welcome! Please choose your language / Добро пожаловать! Выберите ваш язык / Witamy! Wybierz swój język"},
    "help_message": {"en": "ℹ️ <b>Help & Commands</b>\n\n/start - Start the bot\n/language - Change language\n/cart - View cart\n/orders - View orders\n/help - Show this help\n\nUse the menu buttons to browse products and place orders.", "ru": "ℹ️ <b>Справка и команды</b>\n\n/start - Запустить бота\n/language - Сменить язык\n/cart - Показать корзину\n/orders - Показать заказы\n/help - Показать справку\n\nИспользуйте кнопки меню для просмотра товаров и оформления заказов.", "pl": "ℹ️ <b>Pomoc i polecenia</b>\n\n/start - Uruchom bota\n/language - Zmień język\n/cart - Pokaż koszyk\n/orders - Pokaż zamówienia\n/help - Pokaż pomoc\n\nUżyj przycisków menu do przeglądania produktów i składania zamówień."},
    "back": {"en": "◀️ Back", "ru": "◀️ Назад", "pl": "◀️ Wstecz"},
    "back_to_menu": {"en": "🏠 Main Menu", "ru": "🏠 Главное меню", "pl": "🏠 Menu główne"},
    "yes": {"en": "✅ Yes", "ru": "✅ Да", "pl": "✅ Tak"},
    "no": {"en": "❌ No", "ru": "❌ Нет", "pl": "❌ Nie"},
    "cancel": {"en": "🚫 Cancel", "ru": "🚫 Отмена", "pl": "🚫 Anuluj"},
    "skip": {"en": "➡️ Skip", "ru": "➡️ Пропустить", "pl": "➡️ Pomiń"},
    "action_cancelled": {"en": "Action cancelled.", "ru": "Действие отменено.", "pl": "Akcja anulowana."},
    "error_occurred": {"en": "❌ An error occurred. Please try again.", "ru": "❌ Произошла ошибка. Попробуйте еще раз.", "pl": "❌ Wystąpił błąd. Spróbuj ponownie."},
    "unknown_command": {"en": "❓ Unknown command. Use the menu below or /help.", "ru": "❓ Неизвестная команда. Используйте меню или /help.", "pl": "❓ Nieznana komenda. Użyj menu lub /help."},
    "invalid_input": {"en": "❌ Invalid input. Please try again.", "ru": "❌ Неверный ввод. Пожалуйста, попробуйте еще раз.", "pl": "❌ Nieprawidłowe dane. Spróbuj ponownie."},
    "default_username": {"en": "User", "ru": "Пользователь", "pl": "Użytkownik"},
    "reply_keyboard_updated": {"en": "Menu keyboard updated.", "ru": "Клавиатура меню обновлена.", "pl": "Klawiatura menu zaktualizowana."},
    "menu_activated": {"en": ".", "ru": ".", "pl": "."}, # Silent message to ensure reply keyboard is shown
    "user_blocked_message": {"en": "🚫 You are blocked from using this bot.", "ru": "🚫 Вы заблокированы в этом боте.", "pl": "🚫 Jesteś zablokowany w tym bocie."},
    "error_setting_language": {"en": "Error setting language. Please try again.", "ru": "Ошибка установки языка. Попробуйте еще раз.", "pl": "Błąd ustawiania języka. Spróbuj ponownie."},
    "unknown_product": {"en": "Unknown Product", "ru": "Неизвестный товар", "pl": "Nieznany produkt"},
    "not_available_short": {"en": "N/A", "ru": "Н/Д", "pl": "N/D"},

    # Button texts (Main Menu)
    "start_order": {"en": "🛒 Start Order", "ru": "🛒 Начать заказ", "pl": "🛒 Rozpocznij zamówienie"},
    "view_cart": {"en": "🛍 View Cart", "ru": "🛍 Показать корзину", "pl": "🛍 Pokaż koszyk"},
    "my_orders": {"en": "📋 My Orders", "ru": "📋 Мои заказы", "pl": "📋 Moje zamówienia"},
    "help": {"en": "ℹ️ Help", "ru": "ℹ️ Помощь", "pl": "ℹ️ Pomoc"},
    "change_language": {"en": "🌍 Language", "ru": "🌍 Язык", "pl": "🌍 Język"},

    # Order flow texts
    "choose_location": {"en": "📍 Please choose a location:", "ru": "📍 Пожалуйста, выберите локацию:", "pl": "📍 Proszę wybrać lokalizację:"},
    "choose_manufacturer": {"en": "🏭 Choose manufacturer for location <b>{location}</b>:", "ru": "🏭 Выберите производителя для локации <b>{location}</b>:", "pl": "🏭 Wybierz producenta dla lokalizacji <b>{location}</b>:"},
    "choose_product": {"en": "📦 Choose product from <b>{manufacturer}</b>:", "ru": "📦 Выберите товар от <b>{manufacturer}</b>:", "pl": "📦 Wybierz produkt od <b>{manufacturer}</b>:"},
    "product_details": {"en": "📦 <b>{name}</b>\n{description}\n\n💰 Price: {price}\n📦 Available: {stock} {units_short}\n\nHow many would you like?", "ru": "📦 <b>{name}</b>\n{description}\n\n💰 Цена: {price}\n📦 Доступно: {stock} {units_short}\n\nСколько вы хотите?", "pl": "📦 <b>{name}</b>\n{description}\n\n💰 Cena: {price}\n📦 Dostępne: {stock} {units_short}\n\nIle sztuk chcesz?"},
    "units_short": {"en": "units", "ru": "шт.", "pl": "szt."},
    "enter_custom_quantity": {"en": "Please enter the quantity as a number:", "ru": "Пожалуйста, введите количество цифрами:", "pl": "Proszę podać ilość jako liczbę:"},
    "added_to_cart": {"en": "✅ Cart updated!", "ru": "✅ Корзина обновлена!", "pl": "✅ Koszyk zaktualizowany!"},

    # Cart texts
    "cart_empty": {"en": "🛍 Your cart is empty.", "ru": "🛍 Ваша корзина пуста.", "pl": "🛍 Twój koszyk jest pusty."},
    "cart_empty_checkout": {"en": "🛍 Your cart is empty. Cannot proceed to checkout.", "ru": "🛍 Ваша корзина пуста. Оформление заказа невозможно.", "pl": "🛍 Twój koszyk jest pusty. Nie można przejść do kasy."},
    "cart_empty_alert": {"en": "Your cart is empty!", "ru": "Ваша корзина пуста!", "pl": "Twój koszyk jest pusty!"},
    "cart_contents": {"en": "🛍 <b>Your Cart:</b>", "ru": "🛍 <b>Ваша корзина:</b>", "pl": "🛍 <b>Twój koszyk:</b>"},
    "cart_item_format_user": {"en": "<b>{name}</b>{variation} at <i>{location}</i>\n{quantity} x {price_each} = <b>{price_total}</b>", "ru": "<b>{name}</b>{variation} в <i>{location}</i>\n{quantity} x {price_each} = <b>{price_total}</b>", "pl": "<b>{name}</b>{variation} w <i>{location}</i>\n{quantity} x {price_each} = <b>{price_total}</b>"},
    "cart_total": {"en": "\n💰 <b>Total: {total}</b>", "ru": "\n💰 <b>Итого: {total}</b>", "pl": "\n💰 <b>Razem: {total}</b>"},
    "checkout": {"en": "💳 Checkout", "ru": "💳 Оформить заказ", "pl": "💳 Do kasy"},
    "continue_shopping": {"en": "🛒 Continue Shopping", "ru": "🛒 Продолжить покупки", "pl": "🛒 Kontynuuj zakupy"},
    "clear_cart": {"en": "🗑 Clear Cart", "ru": "🗑 Очистить корзину", "pl": "🗑 Wyczyść koszyk"},
    "cart_cleared": {"en": "✅ Your cart has been cleared.", "ru": "✅ Ваша корзина очищена.", "pl": "✅ Twój koszyk został wyczyszczony."},
    "failed_to_clear_cart": {"en": "❌ Failed to clear cart.", "ru": "❌ Не удалось очистить корзину.", "pl": "❌ Nie udało się wyczyścić koszyka."},
    "manage_cart_items_button": {"en": "✏️ Manage Items", "ru": "✏️ Управлять товарами", "pl": "✏️ Zarządzaj przedmiotami"},
    "manage_cart_items_title": {"en": "🛒 Manage Cart Items:", "ru": "🛒 Управление товарами в корзине:", "pl": "🛒 Zarządzanie przedmiotami w koszyku:"},
    "cart_button_change_qty": {"en": "Qty", "ru": "Кол-во", "pl": "Ilość"},
    "cart_button_remove": {"en": "Del", "ru": "Удал.", "pl": "Usuń"},
    "back_to_cart": {"en": "◀️ Back to Cart", "ru": "◀️ Назад в корзину", "pl": "◀️ Wróć do koszyka"},
    "cart_change_item_qty_prompt": {"en": "Change quantity for <b>{product_name}</b> (current: {current_qty}).\nEnter new quantity or choose below:", "ru": "Изменить количество для <b>{product_name}</b> (текущее: {current_qty}).\nВведите новое количество или выберите ниже:", "pl": "Zmień ilość dla <b>{product_name}</b> (obecnie: {current_qty}).\nPodaj nową ilość lub wybierz poniżej:"},
    "back_to_manage_cart": {"en": "◀️ Back to Item List", "ru": "◀️ К списку товаров", "pl": "◀️ Wróć do listy"},
    "cart_item_quantity_updated": {"en": "✅ Item quantity updated.", "ru": "✅ Количество товара обновлено.", "pl": "✅ Ilość przedmiotu zaktualizowana."},
    "cart_item_removed": {"en": "✅ Item removed from cart.", "ru": "✅ Товар удален из корзины.", "pl": "✅ Przedmiot usunięty z koszyka."},
    "cart_item_not_found": {"en": "❌ Item not found in cart.", "ru": "❌ Товар не найден в корзине.", "pl": "❌ Nie znaleziono przedmiotu w koszyku."},
    "invalid_quantity": {"en": "❌ Invalid quantity. Please enter a positive number.", "ru": "❌ Неверное количество. Введите положительное число.", "pl": "❌ Nieprawidłowa ilość. Podaj liczbę dodatnią."},
    "quantity_exceeds_stock": {"en": "❌ Requested {requested} {units_short} of '{product_name}', but only {available} {units_short} available. Please choose a smaller amount.", "ru": "❌ Запрошено {requested} {units_short} товара '{product_name}', но доступно только {available} {units_short}. Пожалуйста, выберите меньшее количество.", "pl": "❌ Żądano {requested} {units_short} produktu '{product_name}', ale dostępne jest tylko {available} {units_short}. Proszę wybrać mniejszą ilość."},
    "quantity_exceeds_stock_at_add": {"en": "❌ Cannot set quantity to {requested} {units_short} for '{product_name}'. Only {available} {units_short} available. Please choose a smaller amount.", "ru": "❌ Невозможно установить количество {requested} {units_short} для '{product_name}'. Доступно только {available} {units_short}. Пожалуйста, выберите меньшее количество.", "pl": "❌ Nie można ustawić ilości na {requested} {units_short} dla '{product_name}'. Dostępne jest tylko {available} {units_short}. Proszę wybrać mniejszą ilość."},
    "product_out_of_stock": {"en": "❌ This product is currently out of stock.", "ru": "❌ Этот товар закончился.", "pl": "❌ Ten produkt jest obecnie niedostępny."},
    "no_locations_available": {"en": "❌ No locations with products currently available.", "ru": "❌ Нет доступных локаций с товарами.", "pl": "❌ Obecnie brak lokalizacji z dostępnymi produktami."},
    "no_manufacturers_available": {"en": "❌ No manufacturers found for this location.", "ru": "❌ Для этой локации производители не найдены.", "pl": "❌ Nie znaleziono producentów dla tej lokalizacji."},
    "no_products_available": {"en": "❌ No products found.", "ru": "❌ Товары не найдены.", "pl": "❌ Nie znaleziono produktów."},
    "no_products_available_manufacturer_location": {"en": "❌ No products available from {manufacturer} at this location.", "ru": "❌ Нет доступных товаров от {manufacturer} в этой локации.", "pl": "❌ Brak dostępnych produktów od {manufacturer} w tej lokalizacji."},
    "failed_to_add_to_cart": {"en": "❌ Failed to update cart. Please try again.", "ru": "❌ Не удалось обновить корзину. Попробуйте еще раз.", "pl": "❌ Nie udało się zaktualizować koszyka. Spróbuj ponownie."},

    # Payment texts
    "choose_payment_method": {"en": "💳 Choose payment method:", "ru": "💳 Выберите способ оплаты:", "pl": "💳 Wybierz metodę płatności:"},
    "payment_cash": {"en": "💵 Cash", "ru": "💵 Наличные", "pl": "💵 Gotówka"},
    "payment_card": {"en": "💳 Card", "ru": "💳 Карта", "pl": "💳 Karta"},
    "payment_online": {"en": "🌐 Online", "ru": "🌐 Онлайн", "pl": "🌐 Online"},
    "payment_method": {"en": "Payment method", "ru": "Способ оплаты", "pl": "Metoda płatności"},

    # Order confirmation
    "order_confirmation": {"en": "📋 <b>Order Confirmation</b>", "ru": "📋 <b>Подтверждение заказа</b>", "pl": "📋 <b>Potwierdzenie zamówienia</b>"},
    "confirm_order": {"en": "✅ Confirm Order", "ru": "✅ Подтвердить заказ", "pl": "✅ Potwierdź zamówienie"},
    "cancel_order_confirmation": {"en": "❌ Cancel Order", "ru": "❌ Отменить Заказ", "pl": "❌ Anuluj Zamówienie"},
    "order_created_successfully": {"en": "✅ Order #{order_id} created successfully!\nYou will be notified once an administrator confirms it.", "ru": "✅ Заказ #{order_id} успешно создан!\nВы получите уведомление, когда администратор его подтвердит.", "pl": "✅ Zamówienie #{order_id} zostało pomyślnie utworzone!\nZostaniesz powiadomiony, gdy administrator je potwierdzi."},
    "order_confirmed": {"en": "Order created!", "ru": "Заказ создан!", "pl": "Zamówienie utworzone!"},
    "order_cancelled": {"en": "❌ Order process cancelled.", "ru": "❌ Процесс заказа отменён.", "pl": "❌ Proces zamówienia anulowany."},
    "order_cancelled_alert": {"en": "Order process cancelled!", "ru": "Процесс заказа отменён!", "pl": "Proces zamówienia anulowany!"},
    "order_creation_failed": {"en": "❌ Order creation failed. Please try again or contact support.", "ru": "❌ Не удалось создать заказ. Попробуйте еще раз или свяжитесь с поддержкой.", "pl": "❌ Tworzenie zamówienia nie powiodło się. Spróbuj ponownie lub skontaktuj się z pomocą techniczną."},
    "order_creation_failed_db": {"en": "❌ Order creation failed due to a database error. Please try again later.", "ru": "❌ Ошибка создания заказа (база данных). Попробуйте позже.", "pl": "❌ Błąd tworzenia zamówienia (baza danych). Spróbuj później."},
    "order_creation_stock_insufficient": {"en": "❌ Cannot create order. Product '{product_name}' has only {available} {units_short} in stock, but {requested} {units_short} were requested in your cart.", "ru": "❌ Невозможно создать заказ. Товара '{product_name}' на складе: {available} {units_short}, запрошено: {requested} {units_short}.", "pl": "❌ Nie można utworzyć zamówienia. Produkt '{product_name}' ma tylko {available} {units_short} na stanie, zażądano {requested} {units_short}."},

    # Order history
    "your_orders": {"en": "📋 <b>Your Orders:</b>", "ru": "📋 <b>Ваши заказы:</b>", "pl": "📋 <b>Twoje zamówienia:</b>"},
    "no_orders_found": {"en": "You have no orders yet.", "ru": "У вас пока нет заказов.", "pl": "Nie masz jeszcze żadnych zamówień."},
    "order_item_user_format": {"en": "Order #{id} ({date})\n{status_emoji} Status: {status}\n💰 Total: {total}", "ru": "Заказ #{id} ({date})\n{status_emoji} Статус: {status}\n💰 Сумма: {total}", "pl": "Zamówienie #{id} ({date})\n{status_emoji} Status: {status}\n💰 Razem: {total}"},

    # Quantity selection
    "max": {"en": "Max", "ru": "Макс", "pl": "Maks"},
    "custom_amount": {"en": "✏️ Custom", "ru": "✏️ Своё", "pl": "✏️ Własna"},

    # Fallback names
    "unknown_location_name": {"en": "Unknown Location", "ru": "Неизвестная локация", "pl": "Nieznana lokalizacja"},
    "unknown_manufacturer_name": {"en": "Unknown Manufacturer", "ru": "Неизвестный производитель", "pl": "Nieznany producent"},
    "unknown_product_name": {"en": "Unknown Product", "ru": "Неизвестный товар", "pl": "Nieznany produkt"}, # Duplicate, for consistency
    "cancel_prompt": {"en": "To cancel, type /cancel", "ru": "Для отмены, введите /cancel", "pl": "Aby anulować, wpisz /cancel"},

    # Admin Panel General
    "admin_panel_title": {"en": "👑 Admin Panel", "ru": "👑 Панель администратора", "pl": "👑 Panel administratora"},
    "admin_access_denied": {"en": "🚫 Access Denied. You are not an administrator.", "ru": "🚫 Доступ запрещен. Вы не администратор.", "pl": "🚫 Dostęp zabroniony. Nie jesteś administratorem."},
    "admin_action_cancelled": {"en": "Admin action cancelled.", "ru": "Действие администратора отменено.", "pl": "Akcja administratora anulowana."},
    "admin_action_failed_no_context": {"en": "❌ Action failed. Context lost. Returning to Admin Panel.", "ru": "❌ Действие не удалось. Контекст утерян. Возврат в Панель администратора.", "pl": "❌ Akcja nie powiodła się. Utracono kontekst. Powrót do Panelu administratora."},
    "admin_action_add": {"en": "➕ Add", "ru": "➕ Добавить", "pl": "➕ Dodaj"},
    "admin_action_list": {"en": "📜 List", "ru": "📜 Список", "pl": "📜 Lista"},
    "admin_action_edit": {"en": "✏️ Edit", "ru": "✏️ Редактировать", "pl": "✏️ Edytuj"},
    "admin_action_delete": {"en": "🗑️ Delete", "ru": "🗑️ Удалить", "pl": "🗑️ Usuń"},
    "back_to_admin_main_menu": {"en": "◀️ Admin Panel", "ru": "◀️ Панель администратора", "pl": "◀️ Panel administratora"},
    "id_prefix": {"en": "ID", "ru": "ID", "pl": "ID"}, # For paginated list item fallback
    "prev_page": {"en": "⬅️ Prev", "ru": "⬅️ Назад", "pl": "⬅️ Poprz."},
    "next_page": {"en": "Next ➡️", "ru": "Далее ➡️", "pl": "Nast. ➡️"},
    "page_display": {"en": "Page {current_page}/{total_pages}", "ru": "Стр. {current_page}/{total_pages}", "pl": "Str. {current_page}/{total_pages}"},
    "not_set": {"en": "Not Set", "ru": "Не задано", "pl": "Nie ustawiono"},

    # Admin Product Management (some existing, some for completeness of section)
    "admin_products_button": {"en": "📦 Products", "ru": "📦 Товары", "pl": "📦 Produkty"},
    "admin_product_management_title": {"en": "📦 Product Management", "ru": "📦 Управление товарами", "pl": "📦 Zarządzanie produktami"},
    "admin_categories_button": {"en": "🗂️ Categories", "ru": "🗂️ Категории", "pl": "🗂️ Kategorie"},
    "admin_manufacturers_button": {"en": "🏭 Manufacturers", "ru": "🏭 Производители", "pl": "🏭 Producenci"},
    "admin_locations_button": {"en": "📍 Locations", "ru": "📍 Локации", "pl": "📍 Lokalizacje"},
    "admin_stock_management_button": {"en": "📈 Stock", "ru": "📈 Остатки", "pl": "📈 Stany magazynowe"},
    "editing_product": {"en": "Editing", "ru": "Редактирование", "pl": "Edycja"},
    "product_field_name_manufacturer_id": {"en": "Manufacturer", "ru": "Производитель", "pl": "Producent"},
    "product_field_name_category_id": {"en": "Category", "ru": "Категория", "pl": "Kategoria"},
    "product_field_name_cost": {"en": "Cost", "ru": "Стоимость", "pl": "Koszt"},
    "product_field_name_sku": {"en": "SKU", "ru": "Артикул (SKU)", "pl": "SKU"},
    "product_field_name_variation": {"en": "Variation", "ru": "Вариация", "pl": "Wariant"},
    "product_field_name_image_url": {"en": "Image URL", "ru": "URL изображения", "pl": "URL obrazu"},
    "product_field_name_localizations": {"en": "Localizations", "ru": "Локализации", "pl": "Lokalizacje"},
    "admin_action_update_stock": {"en": "Update Stock", "ru": "Обновить остатки", "pl": "Aktualizuj stany"},
    "admin_action_add_localization": {"en": "Add Localization", "ru": "Добавить локализацию", "pl": "Dodaj lokalizację"},
    "all_languages_localized": {"en": "All supported languages are localized.", "ru": "Все поддерживаемые языки локализованы.", "pl": "Wszystkie obsługwane języki są zlokalizowane."},
    "no_stock_records_for_product": {"en": "No stock records found for this product at any location.", "ru": "Записи об остатках для этого товара не найдены ни на одной локации.", "pl": "Nie znaleziono żadnych zapisów o stanie magazynowym dla tego produktu w żadnej lokalizacji."},
    "admin_stock_add_to_new_location": {"en": "Add/Set Stock at Another Location", "ru": "Добавить/Установить остаток на другой локации", "pl": "Dodaj/Ustaw stan magazynowy w innej lokalizacji"},
    "back_to_product_options": {"en": "Back to Product Options", "ru": "Назад к опциям товара", "pl": "Wróć do opcji produktu"},
    "back_to_admin_products_menu": {"en": "Back to Product Management", "ru": "Назад к управлению товарами", "pl": "Wróć do zarządzania produktami"},

    # Admin Order Management
    "admin_orders_button": {"en": "🧾 Orders", "ru": "🧾 Заказы", "pl": "🧾 Zamówienia"},
    "admin_orders_title": {"en": "🧾 Order Management", "ru": "🧾 Управление заказами", "pl": "🧾 Zarządzanie zamówieniami"},
    "admin_orders_list_title_status": {"en": "🧾 Orders List ({status})", "ru": "🧾 Список заказов ({status})", "pl": "🧾 Lista zamówień ({status})"},
    "admin_no_orders_found": {"en": "No orders found.", "ru": "Заказы не найдены.", "pl": "Nie znaleziono zamówień."},
    "admin_no_orders_for_status": {"en": "No orders found with status: {status}.", "ru": "Нет заказов со статусом: {status}.", "pl": "Nie znaleziono zamówień o statusie: {status}."},
    "admin_order_summary_list_format": {"en": "{status_emoji} Order #{id} by {user} ({total}) on {date}", "ru": "{status_emoji} Заказ #{id} от {user} ({total}) {date}", "pl": "{status_emoji} Zamówienie #{id} od {user} ({total}) dnia {date}"},
    "back_to_orders_list": {"en": "◀️ Back to Orders List", "ru": "◀️ К списку заказов", "pl": "◀️ Wróć do listy zamówień"},
    "back_to_order_filters": {"en": "◀️ Back to Order Filters", "ru": "◀️ К фильтрам заказов", "pl": "◀️ Wróć do filtrów zamówień"},
    "admin_order_details_title": {"en": "🧾 Order Details: #{order_id}", "ru": "🧾 Детали заказа: #{order_id}", "pl": "🧾 Szczegóły zamówienia: #{order_id}"},
    "user_id_label": {"en": "User ID", "ru": "ID пользователя", "pl": "ID użytkownika"},
    "status_label": {"en": "Status", "ru": "Статус", "pl": "Status"},
    "payment_label": {"en": "Payment", "ru": "Оплата", "pl": "Płatność"},
    "total_label": {"en": "Total", "ru": "Сумма", "pl": "Razem"},
    "created_at_label": {"en": "Created At", "ru": "Создан", "pl": "Utworzono"},
    "updated_at_label": {"en": "Updated At", "ru": "Обновлен", "pl": "Zaktualizowano"},
    "admin_notes_label": {"en": "Admin Notes", "ru": "Заметки администратора", "pl": "Notatki administratora"},
    "order_items_list": {"en": "Items:", "ru": "Товары:", "pl": "Pozycje:"},
    "no_items_found": {"en": "No items in this order.", "ru": "В этом заказе нет товаров.", "pl": "Brak pozycji w tym zamówieniu."},
    "order_item_admin_format": {"en": "  - {name} ({location}): {quantity} x {price} = {total} (Reserved: {reserved_qty})", "ru": "  - {name} ({location}): {quantity} x {price} = {total} (Зарезервировано: {reserved_qty})", "pl": "  - {name} ({location}): {quantity} x {price} = {total} (Zarezerwowane: {reserved_qty})"},
    "admin_order_not_found": {"en": "❌ Order ID {id} not found.", "ru": "❌ Заказ ID {id} не найден.", "pl": "❌ Nie znaleziono zamówienia o ID {id}."},
    "approve_order": {"en": "Approve", "ru": "Одобрить", "pl": "Zatwierdź"},
    "reject_order": {"en": "Reject", "ru": "Отклонить", "pl": "Odrzuć"},
    "admin_action_cancel_order": {"en": "Cancel Order", "ru": "Отменить заказ", "pl": "Anuluj zamówienie"},
    "admin_action_change_status": {"en": "Change Status", "ru": "Изменить статус", "pl": "Zmień status"},
    "admin_enter_rejection_reason": {"en": "Enter reason for rejecting order #{order_id} (or /cancel):", "ru": "Введите причину отклонения заказа #{order_id} (или /cancel):", "pl": "Podaj powód odrzucenia zamówienia #{order_id} (lub /cancel):"},
    "admin_enter_cancellation_reason": {"en": "Enter reason for cancelling order #{order_id} (or /cancel):", "ru": "Введите причину отмены заказа #{order_id} (или /cancel):", "pl": "Podaj powód anulowania zamówienia #{order_id} (lub /cancel):"},
    "admin_select_new_status_prompt": {"en": "Select new status for order #{order_id}:", "ru": "Выберите новый статус для заказа #{order_id}:", "pl": "Wybierz nowy status dla zamówienia #{order_id}:"},
    "admin_order_approved": {"en": "✅ Order #{order_id} approved.", "ru": "✅ Заказ #{order_id} одобрен.", "pl": "✅ Zamówienie #{order_id} zatwierdzone."},
    "admin_order_rejected": {"en": "🚫 Order #{order_id} rejected.", "ru": "🚫 Заказ #{order_id} отклонен.", "pl": "🚫 Zamówienie #{order_id} odrzucone."},
    "admin_order_cancelled": {"en": "❌ Order #{order_id} cancelled by admin.", "ru": "❌ Заказ #{order_id} отменен администратором.", "pl": "❌ Zamówienie #{order_id} anulowane przez administratora."},
    "admin_order_status_updated": {"en": "🔄 Order #{order_id} status updated to {new_status}.", "ru": "🔄 Статус заказа #{order_id} обновлен на {new_status}.", "pl": "🔄 Status zamówienia #{order_id} zaktualizowany na {new_status}."},
    "admin_order_already_processed": {"en": "⚠️ Order #{order_id} has already been processed or is in a final state.", "ru": "⚠️ Заказ #{order_id} уже обработан или находится в конечном статусе.", "pl": "⚠️ Zamówienie #{order_id} zostało już przetworzone lub jest w stanie końcowym."},
    "admin_invalid_status_transition": {"en": "❌ Invalid status transition for order #{order_id}.", "ru": "❌ Недопустимый переход статуса для заказа #{order_id}.", "pl": "❌ Nieprawidłowe przejście statusu dla zamówienia #{order_id}."},
    "order_status_pending_admin_approval": {"en": "Pending Approval", "ru": "Ожидает подтверждения", "pl": "Oczekuje na zatwierdzenie"},
    "order_status_approved": {"en": "Approved", "ru": "Одобрен", "pl": "Zatwierdzone"},
    "order_status_processing": {"en": "Processing", "ru": "В обработке", "pl": "W trakcie realizacji"},
    "order_status_ready_for_pickup": {"en": "Ready for Pickup", "ru": "Готов к выдаче", "pl": "Gotowe do odbioru"},
    "order_status_shipped": {"en": "Shipped", "ru": "Отправлен", "pl": "Wysłane"},
    "order_status_completed": {"en": "Completed", "ru": "Завершен", "pl": "Zakończone"},
    "order_status_cancelled": {"en": "Cancelled", "ru": "Отменен", "pl": "Anulowane"},
    "order_status_rejected": {"en": "Rejected", "ru": "Отклонен", "pl": "Odrzucone"},
    "admin_filter_all_orders_display": {"en": "All Orders", "ru": "Все заказы", "pl": "Wszystkie zamówienia"},

    # Admin User Management
    "admin_users_button": {"en": "👥 Users", "ru": "👥 Пользователи", "pl": "👥 Użytkownicy"},
    "admin_user_management_title": {"en": "👥 User Management", "ru": "👥 Управление пользователями", "pl": "👥 Zarządzanie użytkownikami"},
    "admin_action_list_all_users": {"en": "List All Users", "ru": "Список всех пользователей", "pl": "Lista wszystkich użytkowników"},
    "admin_action_list_blocked_users": {"en": "List Blocked Users", "ru": "Список заблокированных", "pl": "Lista zablokowanych użytkowników"},
    "admin_action_list_active_users": {"en": "List Active Users", "ru": "Список активных пользователей", "pl": "Lista aktywnych użytkowników"},
    "admin_filter_all_users": {"en": "All Users", "ru": "Все пользователи", "pl": "Wszyscy użytkownicy"},
    "admin_filter_blocked_users": {"en": "Blocked Users", "ru": "Заблокированные", "pl": "Zablokowani"},
    "admin_filter_active_users": {"en": "Active Users", "ru": "Активные", "pl": "Aktywni"},
    "admin_users_list_title": {"en": "Users - Filter: {filter}", "ru": "Пользователи - Фильтр: {filter}", "pl": "Użytkownicy - Filtr: {filter}"},
    "admin_no_users_found": {"en": "No users found matching the filter.", "ru": "Не найдено пользователей, соответствующих фильтру.", "pl": "Nie znaleziono użytkowników odpowiadających filtrowi."},
    "admin_user_list_item_format": {"en": "👤 User ID: {id} ({lang}) {status_emoji}", "ru": "👤 ID: {id} ({lang}) {status_emoji}", "pl": "👤 ID: {id} ({lang}) {status_emoji}"}, # Shortened for buttons
    "admin_user_details_title": {"en": "👤 User Details: ID {id}", "ru": "👤 Детали пользователя: ID {id}", "pl": "👤 Szczegóły użytkownika: ID {id}"},
    "language_label": {"en": "Language", "ru": "Язык", "pl": "Język"}, # Re-added for clarity, used in user details
    "blocked_status": {"en": "Blocked", "ru": "Заблокирован", "pl": "Zablokowany"},
    "active_status": {"en": "Active", "ru": "Активен", "pl": "Aktywny"},
    "is_admin_label": {"en": "Is Admin", "ru": "Администратор", "pl": "Jest administratorem"},
    "total_orders_label": {"en": "Total Orders", "ru": "Всего заказов", "pl": "Łącznie zamówień"},
    "joined_date_label": {"en": "Joined", "ru": "Присоединился", "pl": "Dołączył"},
    "admin_action_view_orders": {"en": "View User Orders", "ru": "Заказы пользователя", "pl": "Zamówienia użytkownika"},
    "admin_action_block_user": {"en": "🔒 Block User", "ru": "🔒 Заблокировать", "pl": "🔒 Zablokuj"},
    "admin_action_unblock_user": {"en": "🔓 Unblock User", "ru": "🔓 Разблокировать", "pl": "🔓 Odblokuj"},
    "back_to_user_list": {"en": "◀️ Back to User List", "ru": "◀️ К списку пользователей", "pl": "◀️ Wróć do listy użytkowników"},
    "admin_user_not_found": {"en": "❌ User ID {id} not found.", "ru": "❌ Пользователь ID {id} не найден.", "pl": "❌ Nie znaleziono użytkownika o ID {id}."},
    "admin_confirm_block_user": {"en": "Are you sure you want to block user ID {id}?", "ru": "Вы уверены, что хотите заблокировать пользователя ID {id}?", "pl": "Czy na pewno chcesz zablokować użytkownika o ID {id}?"},
    "admin_confirm_unblock_user": {"en": "Are you sure you want to unblock user ID {id}?", "ru": "Вы уверены, что хотите разблокировать пользователя ID {id}?", "pl": "Czy na pewno chcesz odblokować użytkownika o ID {id}?"},
    "admin_user_blocked_success": {"en": "✅ User ID {id} has been blocked.", "ru": "✅ Пользователь ID {id} заблокирован.", "pl": "✅ Użytkownik o ID {id} został zablokowany."},
    "admin_user_unblocked_success": {"en": "✅ User ID {id} has been unblocked.", "ru": "✅ Пользователь ID {id} разблокирован.", "pl": "✅ Użytkownik o ID {id} został odblokowany."},
    "admin_user_block_failed": {"en": "❌ Failed to block user ID {id}. They might not exist or are already blocked.", "ru": "❌ Не удалось заблокировать пользователя ID {id}. Возможно, он не существует или уже заблокирован.", "pl": "❌ Nie udało się zablokować użytkownika o ID {id}. Może nie istnieć lub jest już zablokowany."},
    "admin_user_unblock_failed": {"en": "❌ Failed to unblock user ID {id}. They might not exist or are already active.", "ru": "❌ Не удалось разблокировать пользователя ID {id}. Возможно, он не существует или уже активен.", "pl": "❌ Nie udało się odblokować użytkownika o ID {id}. Może nie istnieć lub jest już aktywny."},
    "admin_user_block_failed_db": {"en": "❌ Database error while trying to block user ID {id}.", "ru": "❌ Ошибка базы данных при попытке заблокировать пользователя ID {id}.", "pl": "❌ Błąd bazy danych podczas próby zablokowania użytkownika o ID {id}."},
    "admin_user_unblock_failed_db": {"en": "❌ Database error while trying to unblock user ID {id}.", "ru": "❌ Ошибка базы данных при попытке разблокировать пользователя ID {id}.", "pl": "❌ Błąd bazy danych podczas próby odblokowania użytkownika o ID {id}."},

    # Admin Settings
    "admin_settings_button": {"en": "⚙️ Settings", "ru": "⚙️ Настройки", "pl": "⚙️ Ustawienia"},
    "admin_settings_title": {"en": "⚙️ Bot Settings", "ru": "⚙️ Настройки бота", "pl": "⚙️ Ustawienia bota"},
    "admin_current_settings": {"en": "Current Settings (Read-only):", "ru": "Текущие настройки (Только чтение):", "pl": "Obecne ustawienia (Tylko do odczytu):"},
    "setting_bot_token": {"en": "Bot Token (Partial)", "ru": "Токен бота (Частично)", "pl": "Token bota (Częściowo)"},
    "setting_admin_chat_id": {"en": "Primary Admin Chat ID", "ru": "ID основного чата администратора", "pl": "Główne ID czatu administratora"},
    "setting_order_timeout_hours": {"en": "Order Auto-Cancel Timeout (hours)", "ru": "Таймаут авто-отмены заказа (часы)", "pl": "Limit czasu automatycznego anulowania zamówienia (godziny)"},
    "not_set": {"en": "Not Set", "ru": "Не установлено", "pl": "Nie ustawiono"}, # General "Not Set"

    # Admin Statistics
    "admin_stats_button": {"en": "📊 Statistics", "ru": "📊 Статистика", "pl": "📊 Statystyki"},
    "admin_statistics_title": {"en": "📊 Bot Statistics", "ru": "📊 Статистика бота", "pl": "📊 Statystyki bota"},
    "stats_total_users": {"en": "Total Users: {count}", "ru": "Всего пользователей: {count}", "pl": "Łącznie użytkowników: {count}"},
    "stats_active_users": {"en": "Active Users: {count}", "ru": "Активных пользователей: {count}", "pl": "Aktywni użytkownicy: {count}"},
    "stats_blocked_users": {"en": "Blocked Users: {count}", "ru": "Заблокированные: {count}", "pl": "Zablokowani użytkownicy: {count}"},
    "stats_total_orders": {"en": "Total Orders: {count}", "ru": "Всего заказов: {count}", "pl": "Łącznie zamówień: {count}"},
    "stats_pending_orders": {"en": "Pending Approval Orders: {count}", "ru": "Заказы ожидают подтверждения: {count}", "pl": "Zamówienia oczekujące na zatwierdzenie: {count}"},
    "stats_total_products": {"en": "Total Products (approx.): {count}", "ru": "Всего товаров (прибл.): {count}", "pl": "Łącznie produktów (około): {count}"}, # Needs proper count method in ProductService

    # Manufacturer Delete Specific
    "admin_delete_manufacturer_button": {"en": "Delete Manufacturer", "ru": "Удалить производителя", "pl": "Usuń producenta"},
    "admin_select_manufacturer_to_delete_title": {"en": "Select Manufacturer to Delete", "ru": "Выберите производителя для удаления", "pl": "Wybierz producenta do usunięcia"},
    "admin_no_manufacturers_to_delete": {"en": "No manufacturers available to delete.", "ru": "Нет производителей для удаления.", "pl": "Brak producentów do usunięcia."},
    "admin_confirm_delete_manufacturer_prompt": {"en": "Are you sure you want to delete manufacturer '{name}'? If products are linked, this operation will fail.", "ru": "Вы уверены, что хотите удалить производителя '{name}'? Если есть связанные товары, операция не удастся.", "pl": "Czy na pewno chcesz usunąć producenta '{name}'? Jeśli produkty są powiązane, ta operacja nie powiedzie się."},
    "admin_manufacturer_deleted_successfully": {"en": "Manufacturer '{name}' has been deleted successfully.", "ru": "Производитель '{name}' успешно удален.", "pl": "Producent '{name}' został pomyślnie usunięty."},
    "admin_manufacturer_delete_failed": {"en": "Failed to delete manufacturer '{name}'. An unexpected error occurred.", "ru": "Не удалось удалить производителя '{name}'. Произошла непредвиденная ошибка.", "pl": "Nie udało się usunąć producenta '{name}'. Wystąpił nieoczekiwany błąd."},
    "admin_manufacturer_not_found": {"en": "Manufacturer not found.", "ru": "Производитель не найден.", "pl": "Nie znaleziono producenta."},
    "admin_manufacturer_delete_has_products_error": {"en": "Cannot delete manufacturer '{name}' as it is linked to existing products. Please reassign or delete these products first.", "ru": "Невозможно удалить производителя '{name}', так как он связан с существующими товарами. Пожалуйста, переназначьте или удалите эти товары сначала.", "pl": "Nie można usunąć producenta '{name}', ponieważ jest on powiązany z istniejącymi produktami. Najpierw przenieś lub usuń te produkty."},
    "admin_button_edit_manufacturer": {"en": "✏️ Edit Manufacturer", "ru": "✏️ Редактировать производителя", "pl": "✏️ Edytuj producenta"}, # From previous task, ensure it's here
    "admin_select_manufacturer_to_edit_title": {"en": "Select Manufacturer to Edit", "ru": "Выберите производителя для редактирования", "pl": "Wybierz producenta do edycji"}, # From previous task
    "admin_enter_new_manufacturer_name_prompt": {"en": "Current name: {current_name}\nPlease enter the new name for the manufacturer. Type /cancel to abort.", "ru": "Текущее имя: {current_name}\nПожалуйста, введите новое имя для производителя. Введите /cancel для отмены.", "pl": "Obecna nazwa: {current_name}\nProszę podać nową nazwę producenta. Wpisz /cancel, aby anulować."}, # From previous task
    "admin_manufacturer_updated_successfully": {"en": "✅ Manufacturer '{name}' updated successfully.", "ru": "✅ Производитель '{name}' успешно обновлен.", "pl": "✅ Producent '{name}' został pomyślnie zaktualizowany."}, # From previous task
    "admin_manufacturer_update_failed_duplicate": {"en": "❌ Failed to update manufacturer '{name}'. A manufacturer with this name already exists.", "ru": "❌ Не удалось обновить производителя '{name}'. Производитель с таким именем уже существует.", "pl": "❌ Nie udało się zaktualizować producenta '{name}'. Producent o tej nazwie już istnieje."}, # From previous task
    "admin_manufacturer_update_failed_db_error": {"en": "❌ Failed to update manufacturer '{original_name}'. Database error.", "ru": "❌ Не удалось обновить производителя '{original_name}'. Ошибка базы данных.", "pl": "❌ Nie udało się zaktualizować producenta '{original_name}'. Błąd bazy danych."}, # From previous task
    "admin_manufacturer_update_failed_unexpected": {"en": "❌ Failed to update manufacturer '{original_name}'. Unexpected error.", "ru": "❌ Не удалось обновить производителя '{original_name}'. Непредвиденная ошибка.", "pl": "❌ Nie udało się zaktualizować producenta '{original_name}'. Nieoczekiwany błąd."}, # From previous task
    "admin_manufacturer_name_empty_error": {"en": "❌ Manufacturer name cannot be empty. Please try again.", "ru": "❌ Имя производителя не может быть пустым. Попробуйте еще раз.", "pl": "❌ Nazwa producenta nie może być pusta. Spróbuj ponownie."}, # From previous task
    "admin_manufacturer_name_not_changed_error": {"en": "ℹ️ The new name for '{name}' is the same as the current name. No changes made.", "ru": "ℹ️ Новое имя для '{name}' совпадает с текущим. Изменений не внесено.", "pl": "ℹ️ Nowa nazwa dla '{name}' jest taka sama jak obecna. Nie wprowadzono żadnych zmian."}, # From previous task
    "admin_no_manufacturers_found": {"en": "No manufacturers found.", "ru": "Производители не найдены.", "pl": "Nie znaleziono producentów."}, # From previous task, re-used

    # Product Creation Specific
    "admin_prod_enter_manufacturer_id": {"en": "Select Manufacturer for the new product:", "ru": "Выберите производителя для нового товара:", "pl": "Wybierz producenta dla nowego produktu:"},
    "admin_prod_enter_category_id": {"en": "Select Category for the new product (optional):", "ru": "Выберите категорию для нового товара (необязательно):", "pl": "Wybierz kategorię dla nowego produktu (opcjonalnie):"},
    "admin_prod_category_skip_instruction": {"en": "You can skip category selection by clicking the 'Skip' button if available, or if no categories are listed.", "ru": "Вы можете пропустить выбор категории, нажав кнопку 'Пропустить', если доступна, или если категории не отображаются.", "pl": "Możesz pominąć wybór kategorii, klikając przycisk 'Pomiń', jeśli jest dostępny, lub jeśli żadne kategorie nie są wyświetlane."},
    "admin_no_manufacturers_found_for_product_creation": {"en": "No manufacturers found. Cannot create a product without a manufacturer. Please add manufacturers first.", "ru": "Производители не найдены. Невозможно создать товар без производителя. Пожалуйста, сначала добавьте производителей.", "pl": "Nie znaleziono producentów. Nie można utworzyć produktu bez producenta. Najpierw dodaj producentów."},
    "admin_no_categories_found_for_product_creation": {"en": "No categories found. You can proceed without selecting a category.", "ru": "Категории не найдены. Вы можете продолжить без выбора категории.", "pl": "Nie znaleziono kategorii. Możesz kontynuować bez wybierania kategorii."},
    "admin_error_manufacturer_not_found_short": {"en": "Selected manufacturer not found. Please try again.", "ru": "Выбранный производитель не найден. Попробуйте еще раз.", "pl": "Wybrany producent nie został znaleziony. Spróbuj ponownie."},
    "admin_error_category_not_found_short": {"en": "Selected category not found. Please try again or skip.", "ru": "Выбранная категория не найдена. Попробуйте еще раз или пропустите.", "pl": "Wybrana kategoria nie została znaleziona. Spróbuj ponownie lub pomiń."},
    "admin_prod_enter_cost": {"en": "Enter product cost (e.g., 10.99):", "ru": "Введите стоимость товара (например, 10.99):", "pl": "Wprowadź koszt produktu (np. 10.99):"},
    "admin_prod_invalid_cost_format": {"en": "Invalid cost format. Please enter a positive number (e.g., 10.99 or 25).", "ru": "Неверный формат стоимости. Введите положительное число (например, 10.99 или 25).", "pl": "Nieprawidłowy format kosztu. Wprowadź liczbę dodatnią (np. 10.99 lub 25)."},
    "admin_prod_enter_sku": {"en": "Enter product SKU (Stock Keeping Unit, optional):", "ru": "Введите артикул (SKU) товара (необязательно):", "pl": "Wprowadź SKU produktu (opcjonalnie):"},
    "admin_prod_skip_instruction_generic": {"en": "Type '-' to skip this step.", "ru": "Введите '-' чтобы пропустить этот шаг.", "pl": "Wpisz '-', aby pominąć ten krok."},
    "admin_prod_enter_variation": {"en": "Enter product variation (e.g., Color, Size, optional):", "ru": "Введите вариант товара (например, Цвет, Размер, необязательно):", "pl": "Wprowadź wariant produktu (np. Kolor, Rozmiar, opcjonalnie):"},
    "admin_prod_enter_image_url": {"en": "Enter product image URL (optional):", "ru": "Введите URL изображения товара (необязательно):", "pl": "Wprowadź URL obrazu produktu (opcjonalnie):"},
    "admin_prod_select_loc_lang": {"en": "Select language for product name and description:", "ru": "Выберите язык для названия и описания товара:", "pl": "Wybierz język dla nazwy i opisu produktu:"},
    "admin_prod_select_first_loc_lang": {"en": "Let's add the first language for the product name and description. Select a language:", "ru": "Давайте добавим первый язык для названия и описания товара. Выберите язык:", "pl": "Dodajmy pierwszy język dla nazwy i opisu produktu. Wybierz język:"},
    "admin_prod_all_langs_localized_proceed": {"en": "All supported languages have been localized. You can now proceed or add more if you wish (e.g., overwrite existing).", "ru": "Все поддерживаемые языки локализованы. Теперь вы можете продолжить или добавить больше, если хотите (например, перезаписать существующие).", "pl": "Wszystkie obsługiwane języki zostały zlokalizowane. Możesz teraz kontynuować lub dodać więcej, jeśli chcesz (np. nadpisać istniejące)."},
    "admin_prod_done_localizations": {"en": "✅ Done with Localizations", "ru": "✅ Готово с локализациями", "pl": "✅ Zakończono lokalizacje"},
    "admin_prod_enter_loc_name": {"en": "Enter product name for {lang_name}:", "ru": "Введите название товара для {lang_name}:", "pl": "Wprowadź nazwę produktu dla {lang_name}:"},
    "admin_prod_enter_loc_name_forced_first": {"en": "Please provide the product name for {lang_name} to start:", "ru": "Пожалуйста, укажите название товара для {lang_name}, чтобы начать:", "pl": "Podaj nazwę produktu dla {lang_name}, aby rozpocząć:"},
    "admin_prod_error_no_languages_configured": {"en": "Error: No languages configured for localization in the bot. Cannot add product.", "ru": "Ошибка: В боте не настроены языки для локализации. Невозможно добавить товар.", "pl": "Błąd: Brak skonfigurowanych języków do lokalizacji w bocie. Nie można dodać produktu."},
    "admin_prod_loc_name_empty": {"en": "Product name for {lang_name} cannot be empty. Please try again.", "ru": "Название товара для {lang_name} не может быть пустым. Попробуйте еще раз.", "pl": "Nazwa produktu dla {lang_name} nie może być pusta. Spróbuj ponownie."},
    "admin_prod_enter_loc_desc": {"en": "Enter product description for {lang_name} (optional):", "ru": "Введите описание товара для {lang_name} (необязательно):", "pl": "Wprowadź opis produktu dla {lang_name} (opcjonalnie):"},
    "admin_prod_loc_added_ask_more": {"en": "✅ Localization for {lang_name} added. Add another language, or click 'Done'.", "ru": "✅ Локализация для {lang_name} добавлена. Добавьте другой язык или нажмите 'Готово'.", "pl": "✅ Lokalizacja dla {lang_name} dodana. Dodaj kolejny język lub kliknij 'Zakończono'."},
    "admin_prod_confirm_add_details_title": {"en": "📝 Confirm Product Details:", "ru": "📝 Подтвердите детали товара:", "pl": "📝 Potwierdź szczegóły produktu:"},
    "admin_prod_confirm_add_details_prompt": {"en": "Do you want to add this product?", "ru": "Вы хотите добавить этот товар?", "pl": "Czy chcesz dodać ten produkt?"},
    "confirm_and_add_product": {"en": "✅ Yes, Add Product", "ru": "✅ Да, добавить товар", "pl": "✅ Tak, dodaj produkt"},
    "cancel_add_product": {"en": "🚫 Cancel Product Addition", "ru": "🚫 Отменить добавление товара", "pl": "🚫 Anuluj dodawanie produktu"},
    "cancel_add_product_short": {"en": "🚫 Cancel", "ru": "🚫 Отмена", "pl": "🚫 Anuluj"},
    "admin_prod_error_incomplete_data_for_confirmation": {"en": "❌ Error: Incomplete product data for confirmation. Manufacturer, cost, and at least one localization are required. Please start over.", "ru": "❌ Ошибка: Неполные данные товара для подтверждения. Требуются производитель, стоимость и хотя бы одна локализация. Начните заново.", "pl": "❌ Błąd: Niekompletne dane produktu do potwierdzenia. Wymagany jest producent, koszt i co najmniej jedna lokalizacja. Zacznij od nowa."},
    "admin_prod_error_incomplete_data_for_creation": {"en": "❌ Error: Incomplete product data for creation. Action aborted.", "ru": "❌ Ошибка: Неполные данные товара для создания. Действие прервано.", "pl": "❌ Błąd: Niekompletne dane produktu do utworzenia. Akcja przerwana."},
    "admin_product_created_successfully": {"en": "✅ Product '{product_name}' (ID: {product_id}) created successfully!", "ru": "✅ Товар '{product_name}' (ID: {product_id}) успешно создан!", "pl": "✅ Produkt '{product_name}' (ID: {product_id}) został pomyślnie utworzony!"},
    "admin_product_create_failed_sku_duplicate": {"en": "❌ Product creation failed. SKU '{sku}' already exists.", "ru": "❌ Не удалось создать товар. Артикул (SKU) '{sku}' уже существует.", "pl": "❌ Tworzenie produktu nie powiodło się. SKU '{sku}' już istnieje."},
    "admin_error_manufacturer_not_found": {"en": "Manufacturer not found. Cannot create product.", "ru": "Производитель не найден. Невозможно создать товар.", "pl": "Nie znaleziono producenta. Nie można utworzyć produktu."},
    "admin_error_category_not_found": {"en": "Category not found. Cannot create product with this category.", "ru": "Категория не найдена. Невозможно создать товар с этой категорией.", "pl": "Nie znaleziono kategorii. Nie można utworzyć produktu z tą kategorią."},
    "admin_product_create_failed_no_localization": {"en": "Product creation failed. At least one localization (name/description) is required.", "ru": "Не удалось создать товар. Требуется хотя бы одна локализация (название/описание).", "pl": "Tworzenie produktu nie powiodło się. Wymagana jest co najmniej jedna lokalizacja (nazwa/opis)."},
    "admin_product_create_failed_db_error": {"en": "Product creation failed due to a database error.", "ru": "Не удалось создать товар из-за ошибки базы данных.", "pl": "Tworzenie produktu nie powiodło się z powodu błędu bazy danych."},
    "admin_product_create_failed_unexpected": {"en": "Product creation failed due to an unexpected error.", "ru": "Не удалось создать товар из-за непредвиденной ошибки.", "pl": "Tworzenie produktu nie powiodło się z powodu nieoczekiwanego błędu."},
    "name_label": {"en": "Name", "ru": "Имя", "pl": "Nazwa"}, # Generic, used in confirmation
    "description_label": {"en": "Description", "ru": "Описание", "pl": "Opis"}, # Generic, used in confirmation
    "admin_prod_no_localizations_added_summary": {"en": "No localizations were added.", "ru": "Локализации не были добавлены.", "pl": "Nie dodano żadnych lokalizacji."},
    "not_applicable_short": {"en": "N/A", "ru": "Н/П", "pl": "N/D"}, # For category if skipped
    "back_to_product_management": {"en": "◀️ Product Menu", "ru": "◀️ Меню товаров", "pl": "◀️ Menu produktów"}, # For cancel during product add sub-flows

    # Product Update Specific
    "admin_prod_edit_options_title": {"en": "✏️ Editing Product: {product_name}", "ru": "✏️ Редактирование товара: {product_name}", "pl": "✏️ Edycja produktu: {product_name}"},
    "admin_prod_prompt_edit_cost": {"en": "Enter new cost for {product_name}:", "ru": "Введите новую стоимость для {product_name}:", "pl": "Wprowadź nowy koszt dla {product_name}:"},
    "admin_prod_prompt_edit_sku": {"en": "Enter new SKU for {product_name} (or '-' to remove):", "ru": "Введите новый артикул (SKU) для {product_name} (или '-' для удаления):", "pl": "Wprowadź nowe SKU dla {product_name} (lub '-' aby usunąć):"},
    "admin_prod_prompt_edit_variation": {"en": "Enter new variation for {product_name} (or '-' to remove):", "ru": "Введите новый вариант для {product_name} (или '-' для удаления):", "pl": "Wprowadź nowy wariant dla {product_name} (lub '-' aby usunąć):"},
    "admin_prod_prompt_edit_image_url": {"en": "Enter new image URL for {product_name} (or '-' to remove):", "ru": "Введите новый URL изображения для {product_name} (или '-' для удаления):", "pl": "Wprowadź nowy URL obrazu dla {product_name} (lub '-' aby usunąć):"},
    "admin_prod_prompt_edit_manufacturer": {"en": "Select new manufacturer for {product_name}:", "ru": "Выберите нового производителя для {product_name}:", "pl": "Wybierz nowego producenta dla {product_name}:"},
    "admin_prod_prompt_edit_category": {"en": "Select new category for {product_name} (or skip to remove):", "ru": "Выберите новую категорию для {product_name} (или пропустите для удаления):", "pl": "Wybierz nową kategorię dla {product_name} (lub pomiń, aby usunąć):"},
    "skip_and_remove_category": {"en": "Skip & Remove Category", "ru": "Пропустить и удалить категорию", "pl": "Pomiń i usuń kategorię"},
    "admin_prod_updated_field_successfully": {"en": "✅ {field_name_loc} for product {product_name} updated to {new_value}.", "ru": "✅ Поле '{field_name_loc}' для товара {product_name} обновлено на {new_value}.", "pl": "✅ Pole '{field_name_loc}' dla produktu {product_name} zaktualizowane na {new_value}."},
    "admin_prod_updated_association_successfully": {"en": "✅ {association_name} for product {product_name} updated to {new_value}.", "ru": "✅ Связь '{association_name}' для товара {product_name} обновлена на {new_value}.", "pl": "✅ Powiązanie '{association_name}' dla produktu {product_name} zaktualizowane na {new_value}."},
    "admin_prod_update_failed_generic": {"en": "❌ Failed to update product field.", "ru": "❌ Не удалось обновить поле товара.", "pl": "❌ Nie udało się zaktualizować pola produktu."},
    "admin_prod_update_failed_db_error": {"en": "❌ Database error while updating product. SKU '{sku}' might already exist or another issue occurred.", "ru": "❌ Ошибка базы данных при обновлении товара. Артикул '{sku}' может уже существовать или произошла другая проблема.", "pl": "❌ Błąd bazy danych podczas aktualizacji produktu. SKU '{sku}' może już istnieć lub wystąpił inny problem."},
    "admin_prod_update_failed_db_error_association": {"en": "❌ Database error while updating product {association_name}. The selected entity might not exist.", "ru": "❌ Ошибка базы данных при обновлении {association_name} товара. Выбранная сущность может не существовать.", "pl": "❌ Błąd bazy danych podczas aktualizacji {association_name} produktu. Wybrana encja może nie istnieć."},
    "admin_prod_update_failed_invalid_association": {"en": "❌ Invalid association type for product update.", "ru": "❌ Неверный тип связи для обновления товара.", "pl": "❌ Nieprawidłowy typ powiązania dla aktualizacji produktu."},
    "admin_prod_error_manufacturer_cannot_be_none": {"en": "❌ Manufacturer cannot be removed or set to none. Product must have a manufacturer.", "ru": "❌ Производитель не может быть удален или не указан. Товар должен иметь производителя.", "pl": "❌ Producent nie może zostać usunięty ani ustawiony jako brak. Produkt musi mieć producenta."},
    "admin_prod_invalid_input_for_field": {"en": "❌ Invalid input for the field. Please try again.", "ru": "❌ Неверный ввод для поля. Пожалуйста, попробуйте еще раз.", "pl": "❌ Nieprawidłowe dane dla pola. Spróbuj ponownie."},
    "admin_product_update_failed_sku_duplicate": {"en": "❌ Failed to update product. The SKU '{value}' already exists for another product.", "ru": "❌ Не удалось обновить товар. Артикул (SKU) '{value}' уже используется для другого товара.", "pl": "❌ Nie udało się zaktualizować produktu. SKU '{value}' już istnieje dla innego produktu."},
    "admin_prod_edit_locs_menu_title": {"en": "✏️ Manage Localizations for: {product_name}", "ru": "✏️ Управление локализациями для: {product_name}", "pl": "✏️ Zarządzaj lokalizacjami dla: {product_name}"},
    "admin_prod_edit_loc_enter_name": {"en": "Enter new name for {lang_name} localization:", "ru": "Введите новое имя для локализации ({lang_name}):", "pl": "Wprowadź nową nazwę dla lokalizacji ({lang_name}):"},
    "admin_prod_add_loc_select_lang": {"en": "Select language to add new localization:", "ru": "Выберите язык для добавления новой локализации:", "pl": "Wybierz język, aby dodać nową lokalizację:"},
    "admin_prod_all_langs_already_localized": {"en": "All supported languages are already localized for this product. You can edit existing ones.", "ru": "Все поддерживаемые языки уже локализованы для этого товара. Вы можете отредактировать существующие.", "pl": "Wszystkie obsługiwane języki są już zlokalizowane dla tego produktu. Możesz edytować istniejące."},
    "admin_prod_localization_saved_successfully": {"en": "✅ Localization for {lang_name} saved successfully.", "ru": "✅ Локализация для {lang_name} успешно сохранена.", "pl": "✅ Lokalizacja dla {lang_name} została pomyślnie zapisana."},
    "admin_prod_localization_save_failed_db": {"en": "❌ Database error while saving localization for {lang_name}.", "ru": "❌ Ошибка базы данных при сохранении локализации для {lang_name}.", "pl": "❌ Błąd bazy danych podczas zapisywania lokalizacji dla {lang_name}."},
    "admin_prod_localization_save_failed_unexpected": {"en": "❌ Unexpected error while saving localization for {lang_name}.", "ru": "❌ Непредвиденная ошибка при сохранении локализации для {lang_name}.", "pl": "❌ Nieoczekiwany błąd podczas zapisywania lokalizacji dla {lang_name}."},
    "cancel_prompt_short": {"en": "{command} to cancel", "ru": "{command} для отмены", "pl": "{command} aby anulować"},
    "cancel_prompt_short_to_loc_menu": {"en": "{command} to return to localizations menu for this product (ID: {product_id})", "ru": "{command} для возврата в меню локализаций этого товара (ID: {product_id})", "pl": "{command} aby wrócić do menu lokalizacji tego produktu (ID: {product_id})"},
    "loading_text": {"en": "Loading...", "ru": "Загрузка...", "pl": "Ładowanie..."}, # Generic loading text

    # Product Deletion Specific
    "admin_prod_confirm_delete_prompt": {"en": "Are you sure you want to delete product '{product_name}' (ID: {product_id})? This action cannot be undone.", "ru": "Вы уверены, что хотите удалить товар '{product_name}' (ID: {product_id})? Это действие необратимо.", "pl": "Czy na pewno chcesz usunąć produkt '{product_name}' (ID: {product_id})? Tej akcji nie można cofnąć."},
    "admin_product_deleted_successfully": {"en": "🗑 Product '{product_name}' (ID: {product_id}) has been deleted.", "ru": "🗑 Товар '{product_name}' (ID: {product_id}) был удален.", "pl": "🗑 Produkt '{product_name}' (ID: {product_id}) został usunięty."},
    "admin_product_delete_failed_in_use": {"en": "⚠️ Failed to delete product '{product_name}' (ID: {product_id}) as it is currently in use (e.g., in orders or stock records).", "ru": "⚠️ Не удалось удалить товар '{product_name}' (ID: {product_id}), так как он используется (например, в заказах или складских записях).", "pl": "⚠️ Nie udało się usunąć produktu '{product_name}' (ID: {product_id}), ponieważ jest on obecnie w użyciu (np. w zamówieniach lub ewidencji magazynowej)."},
    "admin_product_delete_failed_generic": {"en": "❌ Failed to delete product '{product_name}' (ID: {product_id}) due to a database error.", "ru": "❌ Не удалось удалить товар '{product_name}' (ID: {product_id}) из-за ошибки базы данных.", "pl": "❌ Nie udało się usunąć produktu '{product_name}' (ID: {product_id}) z powodu błędu bazy danych."},
    "admin_product_delete_failed_unexpected": {"en": "❌ Failed to delete product '{product_name}' (ID: {product_id}) due to an unexpected error.", "ru": "❌ Не удалось удалить товар '{product_name}' (ID: {product_id}) из-за непредвиденной ошибки.", "pl": "❌ Nie udało się usunąć produktu '{product_name}' (ID: {product_id}) z powodu nieoczekiwanego błędu."},
    # admin_product_not_found is already generic and can be reused.

    # Location Service Specific
    "not_specified_placeholder": {"en": "Not specified", "ru": "Не указано", "pl": "Nie określono"},
    "no_address_placeholder": {"en": "No address", "ru": "Без адреса", "pl": "Brak adresu"},
    "admin_location_already_exists_error": {"en": "Error: A location with this name already exists.", "ru": "Ошибка: Локация с таким названием уже существует.", "pl": "Błąd: Lokalizacja o tej nazwie już istnieje."},
    "admin_location_create_failed_error": {"en": "Error: Failed to create the location.", "ru": "Ошибка: Не удалось создать локацию.", "pl": "Błąd: Nie udało się utworzyć lokalizacji."},
    "admin_db_error_generic": {"en": "Database error. Please try again later.", "ru": "Ошибка базы данных. Пожалуйста, попробуйте позже.", "pl": "Błąd bazy danych. Spróbuj ponownie później."},
    "admin_unexpected_error_generic": {"en": "An unexpected error occurred. Please try again later.", "ru": "Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.", "pl": "Wystąpił nieoczekiwany błąd. Spróbuj ponownie później."},
    "admin_location_name_exists_error": {"en": "Error: Another location with this name already exists.", "ru": "Ошибка: Другая локация с таким названием уже существует.", "pl": "Błąd: Inna lokalizacja o tej nazwie już istnieje."},
    "admin_location_not_found_error": {"en": "Error: Location not found.", "ru": "Ошибка: Локация не найдена.", "pl": "Błąd: Nie znaleziono lokalizacji."},
    "admin_location_update_failed_error": {"en": "Error: Failed to update the location.", "ru": "Ошибка: Не удалось обновить локацию.", "pl": "Błąd: Nie udało się zaktualizować lokalizacji."},
    "admin_location_deleted_successfully": {"en": "Location '{name}' has been deleted successfully.", "ru": "Локация '{name}' успешно удалена.", "pl": "Lokalizacja '{name}' została pomyślnie usunięta."},
    "admin_location_delete_has_dependencies_error": {"en": "Error: Cannot delete location '{name}' as it has associated records (e.g., stock, orders). Please remove dependencies first.", "ru": "Ошибка: Невозможно удалить локацию '{name}', так как она связана с записями (например, остатки, заказы). Сначала удалите зависимости.", "pl": "Błąd: Nie można usunąć lokalizacji '{name}', ponieważ ma powiązane rekordy (np. stany magazynowe, zamówienia). Najpierw usuń zależności."},
    "admin_location_delete_failed_error": {"en": "Error: Failed to delete location '{name}'.", "ru": "Ошибка: Не удалось удалить локацию '{name}'.", "pl": "Błąd: Nie udało się usunąć lokalizacji '{name}'."},
}

def get_text(key: str, language: Optional[str], default: Optional[str] = None, **kwargs: Any) -> str: # Ensure kwargs is here
    """
    Get localized text for a given key and language.
    Falls back to English or a provided default if the key or language is not found.
    Supports keyword arguments for formatting.
    """
    if language is None:
        language = "en" # Default to English if no language provided

    final_text = f"[[{key}]]" # Default if nothing found

    lang_texts = TEXTS.get(key)
    if lang_texts:
        text_for_lang = lang_texts.get(language)
        if text_for_lang is not None:
            final_text = text_for_lang
        else:
            # Fallback to English if specific language not found for the key
            text_en = lang_texts.get("en")
            if text_en is not None:
                # logger.debug(f"Text key '{key}' not found for language '{language}', falling back to English.")
                final_text = text_en
            # If English also not found, final_text remains "[[{key}]]"
    
    # If key itself was not found at all, lang_texts would be None
    # In this case, if a default is provided, use it. Otherwise, final_text is "[[{key}]]"
    if lang_texts is None and default is not None:
        # logger.warning(f"Text key '{key}' not found. Using provided default.")
        final_text = default
    
    # Attempt to format the string if kwargs are provided
    if kwargs:
        try:
            return final_text.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing key '{e}' in text for '{key}' with language '{language}' and format args {kwargs}. Text: '{final_text}'")
            # Return the unformatted string or a modified error indicator
            return f"[[FORMAT_ERROR:{key}]]" 
            
    return final_text


def get_all_texts_for_language(language: str) -> Dict[str, str]:
    """Get all texts for a specific language, falling back to English if needed."""
    result = {}
    for key, translations in TEXTS.items():
        result[key] = translations.get(language, translations.get("en", f"[[{key}]]"))
    return result



