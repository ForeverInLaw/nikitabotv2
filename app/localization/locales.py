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
}

def get_text(key: str, language: Optional[str], default: Optional[str] = None) -> str:
    """
    Get localized text for a given key and language.
    Falls back to English or a provided default if the key or language is not found.
    """
    if language is None:
        language = "en" # Default to English if no language provided

    lang_texts = TEXTS.get(key)
    if lang_texts:
        text = lang_texts.get(language)
        if text is not None:
            return text
        # Fallback to English if specific language not found for the key
        text_en = lang_texts.get("en")
        if text_en is not None:
            # Log fallback for missing specific language translation
            # logger.debug(f"Text key '{key}' not found for language '{language}', falling back to English.")
            return text_en
    
    # If key itself is not found, or English version of key is not found
    if default is not None:
        # logger.warning(f"Text key '{key}' not found. Using provided default.")
        return default
    
    # Fallback for completely missing key, return key itself to indicate missing translation
    # logger.error(f"Text key '{key}' not found, and no default provided. Returning key name.")
    return f"[[{key}]]" # Indicate missing translation


def get_all_texts_for_language(language: str) -> Dict[str, str]:
    """Get all texts for a specific language, falling back to English if needed."""
    result = {}
    for key, translations in TEXTS.items():
        result[key] = translations.get(language, translations.get("en", f"[[{key}]]"))
    return result



