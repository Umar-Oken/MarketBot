import re
from decimal import Decimal

from sqlalchemy import select

from db import database
from db.models import Category, Product
from db.product_photos import product_photo_file
from db.storage import configure_file_storage


CATEGORIES = [
    {
        "name": "Elektronika",
        "photo": "images/categories/electronics.jpg",
        "description": "Smartfon, noutbuk, audio va kundalik elektronika mahsulotlari.",
    },
    {
        "name": "Smartfonlar",
        "parent": "Elektronika",
        "photo": "images/categories/smartphones.jpg",
        "description": "Apple, Samsung, Xiaomi va Google smartfonlari.",
    },
    {
        "name": "Noutbuklar",
        "parent": "Elektronika",
        "photo": "images/categories/laptops.jpg",
        "description": "Ish, o'qish va biznes uchun noutbuklar.",
    },
    {
        "name": "Audio texnika",
        "parent": "Elektronika",
        "photo": "images/categories/audio.jpg",
        "description": "Quloqchin, portativ kolonka va simsiz audio qurilmalar.",
    },
    {
        "name": "Kompyuter aksessuarlari",
        "photo": "images/categories/computer-accessories.jpg",
        "description": "Klaviatura, sichqoncha, power bank va boshqa aksessuarlar.",
    },
    {
        "name": "Monitorlar",
        "parent": "Kompyuter aksessuarlari",
        "photo": "images/categories/monitors.jpg",
        "description": "Ofis, dizayn va gaming uchun monitorlar.",
    },
    {
        "name": "Klaviatura va sichqonchalar",
        "parent": "Kompyuter aksessuarlari",
        "photo": "images/categories/keyboards-mice.jpg",
        "description": "Simsiz va mexanik klaviatura hamda sichqonchalar.",
    },
    {
        "name": "Maishiy texnika",
        "photo": "images/categories/home-appliances.jpg",
        "description": "Uy uchun yirik va kichik maishiy texnika.",
    },
    {
        "name": "Sovutkichlar",
        "parent": "Maishiy texnika",
        "photo": "images/categories/refrigerators.jpg",
        "description": "Samsung, LG, Bosch va Artel sovutkichlari.",
    },
    {
        "name": "Changyutkichlar",
        "parent": "Maishiy texnika",
        "photo": "images/categories/vacuum-cleaners.jpg",
        "description": "Uy tozaligi uchun simli va simsiz changyutkichlar.",
    },
    {
        "name": "Uy va oshxona",
        "photo": "images/categories/home-kitchen.jpg",
        "description": "Oshxona texnikasi, idish-tovoq va uy uchun foydali mahsulotlar.",
    },
    {
        "name": "Oshxona jihozlari",
        "parent": "Uy va oshxona",
        "photo": "images/categories/kitchen-appliances.jpg",
        "description": "Airfryer, blender, toaster va oshxona kombaynlari.",
    },
    {
        "name": "Idish-tovoqlar",
        "parent": "Uy va oshxona",
        "photo": "images/categories/cookware.jpg",
        "description": "Kastryulka, tova, pishirish idishlari va servis to'plamlari.",
    },
    {
        "name": "Shaxsiy parvarish",
        "photo": "images/categories/personal-care.jpg",
        "description": "Soch, soqol va og'iz parvarishi uchun qurilmalar.",
    },
    {
        "name": "Bolalar mahsulotlari",
        "photo": "images/categories/kids.jpg",
        "description": "Bolalar uchun konstruktor, mashina va rivojlantiruvchi o'yinchoqlar.",
    },
]



PRODUCTS = [
    {
        "category": "Smartfonlar",
        "name": "Apple iPhone 15 Pro 256GB",
        "description": "A17 Pro chip, 6.1 dyuym Super Retina XDR display va titanium korpus.",
        "price": "17990000.00",
        "stock_quantity": 8,
    },
    {
        "category": "Smartfonlar",
        "name": "Apple iPhone 15 128GB",
        "description": "Dynamic Island, 48 MP asosiy kamera va USB-C portli Apple smartfoni.",
        "price": "11990000.00",
        "stock_quantity": 12,
    },
    {
        "category": "Smartfonlar",
        "name": "Samsung Galaxy S24 Ultra 256GB",
        "description": "S Pen, 200 MP kamera va Galaxy AI imkoniyatlariga ega flagship smartfon.",
        "price": "15990000.00",
        "stock_quantity": 7,
    },
    {
        "category": "Smartfonlar",
        "name": "Samsung Galaxy A55 5G 256GB",
        "description": "Super AMOLED display, 5G va 50 MP kamera bilan o'rta segment smartfon.",
        "price": "4750000.00",
        "stock_quantity": 20,
    },
    {
        "category": "Smartfonlar",
        "name": "Xiaomi Redmi Note 13 Pro 256GB",
        "description": "120 Hz AMOLED display, 200 MP kamera va tez quvvatlanish.",
        "price": "3899000.00",
        "stock_quantity": 24,
    },
    {
        "category": "Smartfonlar",
        "name": "Google Pixel 8 128GB",
        "description": "Google Tensor G3 chipi, sof Android va kuchli kamera algoritmlari.",
        "price": "7490000.00",
        "stock_quantity": 6,
    },
    {
        "category": "Noutbuklar",
        "name": "Apple MacBook Air 13 M3 256GB",
        "description": "M3 chip, 13.6 dyuym Liquid Retina display va yengil alyuminiy korpus.",
        "price": "14990000.00",
        "stock_quantity": 5,
    },
    {
        "category": "Noutbuklar",
        "name": "Apple MacBook Pro 14 M3 Pro 512GB",
        "description": "Professional ishlar uchun M3 Pro chipli 14 dyuym MacBook Pro.",
        "price": "27990000.00",
        "stock_quantity": 3,
    },
    {
        "category": "Noutbuklar",
        "name": "Lenovo ThinkPad E16 Gen 1",
        "description": "Biznes uchun mustahkam korpusli, qulay klaviaturali 16 dyuym noutbuk.",
        "price": "9200000.00",
        "stock_quantity": 9,
    },
    {
        "category": "Noutbuklar",
        "name": "ASUS Zenbook 14 OLED",
        "description": "OLED display, ixcham korpus va yuqori unumdorlikka ega ultrabook.",
        "price": "12600000.00",
        "stock_quantity": 6,
    },
    {
        "category": "Noutbuklar",
        "name": "HP Pavilion 15",
        "description": "O'qish, ofis va kundalik ishlar uchun universal 15 dyuym noutbuk.",
        "price": "7800000.00",
        "stock_quantity": 13,
    },
    {
        "category": "Noutbuklar",
        "name": "Acer Aspire 5",
        "description": "Full HD ekran, SSD xotira va kundalik ishlash uchun qulay konfiguratsiya.",
        "price": "6900000.00",
        "stock_quantity": 11,
    },
    {
        "category": "Audio texnika",
        "name": "Sony WH-1000XM5",
        "description": "Faol shovqinni pasaytirish va yuqori sifatli ovozga ega simsiz quloqchin.",
        "price": "4290000.00",
        "stock_quantity": 10,
    },
    {
        "category": "Audio texnika",
        "name": "Apple AirPods Pro 2",
        "description": "Adaptive Audio, ANC va MagSafe quvvatlash qutisi bilan TWS quloqchin.",
        "price": "2890000.00",
        "stock_quantity": 18,
    },
    {
        "category": "Audio texnika",
        "name": "JBL Charge 5",
        "description": "IP67 himoyali, kuchli bassli portativ Bluetooth kolonka.",
        "price": "1890000.00",
        "stock_quantity": 14,
    },
    {
        "category": "Audio texnika",
        "name": "Samsung Galaxy Buds2 Pro",
        "description": "ANC, 360 Audio va ixcham dizaynga ega Samsung simsiz quloqchini.",
        "price": "1590000.00",
        "stock_quantity": 16,
    },
    {
        "category": "Audio texnika",
        "name": "Anker Soundcore Life Q30",
        "description": "Uzoq batareya va shovqinni pasaytirish funksiyasiga ega quloqchin.",
        "price": "890000.00",
        "stock_quantity": 22,
    },
    {
        "category": "Sovutkichlar",
        "name": "Samsung RB33B610EBN/WT",
        "description": "No Frost texnologiyasi va tejamkor inverter kompressorli sovutkich.",
        "price": "8950000.00",
        "stock_quantity": 4,
    },
    {
        "category": "Sovutkichlar",
        "name": "LG DoorCooling+ GA-B459CQWL",
        "description": "DoorCooling+ sovitish tizimi va Smart Inverter kompressor.",
        "price": "8700000.00",
        "stock_quantity": 5,
    },
    {
        "category": "Sovutkichlar",
        "name": "Bosch KGN36NL30U",
        "description": "No Frost, MultiAirflow va keng ichki hajmga ega Bosch sovutkichi.",
        "price": "10500000.00",
        "stock_quantity": 3,
    },
    {
        "category": "Sovutkichlar",
        "name": "Artel HD 455 RWEN",
        "description": "Uy uchun keng hajmli, qulay polkali ikki kamerali sovutkich.",
        "price": "5490000.00",
        "stock_quantity": 7,
    },
    {
        "category": "Changyutkichlar",
        "name": "Dyson V15 Detect Absolute",
        "description": "Lazerli chang aniqlash va kuchli so'rish tizimiga ega simsiz changyutkich.",
        "price": "10990000.00",
        "stock_quantity": 3,
    },
    {
        "category": "Changyutkichlar",
        "name": "Samsung Jet 75 Complete",
        "description": "Yengil korpusli, HEPA filtrli va turli nasadkali simsiz changyutkich.",
        "price": "5990000.00",
        "stock_quantity": 6,
    },
    {
        "category": "Changyutkichlar",
        "name": "Philips PowerPro Compact FC9330",
        "description": "PowerCyclone 5 texnologiyasi va ixcham dizaynli konteynerli changyutkich.",
        "price": "1690000.00",
        "stock_quantity": 15,
    },
    {
        "category": "Changyutkichlar",
        "name": "Artel VCC 0120",
        "description": "Kundalik tozalash uchun qulay, hamyonbop konteynerli changyutkich.",
        "price": "899000.00",
        "stock_quantity": 19,
    },
    {
        "category": "Oshxona jihozlari",
        "name": "Philips HD9252/90 Airfryer",
        "description": "Yog'ni kam ishlatib pishirish uchun 4.1 litrli airfryer.",
        "price": "1690000.00",
        "stock_quantity": 12,
    },
    {
        "category": "Oshxona jihozlari",
        "name": "Tefal Easy Fry Compact EY3018",
        "description": "Ixcham oshxonalar uchun 1.6 litrli issiq havo friturnitsasi.",
        "price": "1290000.00",
        "stock_quantity": 10,
    },
    {
        "category": "Oshxona jihozlari",
        "name": "Bosch MUMS2EW00 oshxona kombayni",
        "description": "Xamir qorish, aralashtirish va kundalik pishiriqlar uchun kombayn.",
        "price": "2490000.00",
        "stock_quantity": 8,
    },
    {
        "category": "Oshxona jihozlari",
        "name": "Braun MultiQuick 7 MQ7035X",
        "description": "Qo'l blenderi, maydalagich va ko'pirtirgich to'plami.",
        "price": "1550000.00",
        "stock_quantity": 11,
    },
    {
        "category": "Oshxona jihozlari",
        "name": "Moulinex Subito LT260D10 toaster",
        "description": "2 bo'limli, qizartirish darajasi sozlanadigan ixcham toaster.",
        "price": "499000.00",
        "stock_quantity": 21,
    },
    {
        "category": "Idish-tovoqlar",
        "name": "Tefal Ingenio Emotion 10 pcs",
        "description": "Olinadigan tutqichli zanglamas po'latdan tayyorlangan tova va kastryulka to'plami.",
        "price": "2450000.00",
        "stock_quantity": 6,
    },
    {
        "category": "Idish-tovoqlar",
        "name": "Luminarc Diwali 18 pcs dinner set",
        "description": "6 kishilik oq rangli tarelka va kosa servis to'plami.",
        "price": "799000.00",
        "stock_quantity": 14,
    },
    {
        "category": "Idish-tovoqlar",
        "name": "Pyrex Classic glass baking dish",
        "description": "Pechda pishirish uchun issiqqa chidamli shisha forma.",
        "price": "239000.00",
        "stock_quantity": 25,
    },
    {
        "category": "Idish-tovoqlar",
        "name": "Rondell Mocco & Latte pan 26cm",
        "description": "26 sm diametrli, yopishmaydigan qoplamali kundalik tova.",
        "price": "489000.00",
        "stock_quantity": 18,
    },
    {
        "category": "Shaxsiy parvarish",
        "name": "Dyson Supersonic HD07",
        "description": "Tez quritish va issiqlikni nazorat qilish funksiyali premium fen.",
        "price": "7990000.00",
        "stock_quantity": 4,
    },
    {
        "category": "Shaxsiy parvarish",
        "name": "Philips Series 5000 BHD510 hair dryer",
        "description": "ThermoShield texnologiyasi va ionizatsiyali soch quritgich.",
        "price": "799000.00",
        "stock_quantity": 17,
    },
    {
        "category": "Shaxsiy parvarish",
        "name": "Philips OneBlade QP2724/20",
        "description": "Soqolni qirqish, kontur qilish va tarash uchun universal trimmer.",
        "price": "649000.00",
        "stock_quantity": 20,
    },
    {
        "category": "Shaxsiy parvarish",
        "name": "Braun Series 5 51-B1000s",
        "description": "Suv o'tkazmaydigan, AutoSense texnologiyali elektr soqol olgich.",
        "price": "1590000.00",
        "stock_quantity": 9,
    },
    {
        "category": "Shaxsiy parvarish",
        "name": "Oral-B Pro 3 3000",
        "description": "Bosim sensori va 3 rejimli elektr tish cho'tkasi.",
        "price": "749000.00",
        "stock_quantity": 16,
    },
    {
        "category": "Bolalar mahsulotlari",
        "name": "LEGO Classic 10698",
        "description": "Ijodiy qurish uchun 790 dona rangli LEGO g'ishtchalari to'plami.",
        "price": "999000.00",
        "stock_quantity": 13,
    },
    {
        "category": "Bolalar mahsulotlari",
        "name": "LEGO Technic Bugatti Bolide 42151",
        "description": "Avtomobil ishqibozlari uchun Bugatti Bolide konstruktor modeli.",
        "price": "749000.00",
        "stock_quantity": 10,
    },
    {
        "category": "Bolalar mahsulotlari",
        "name": "Hot Wheels 20-Car Gift Pack",
        "description": "20 dona metall o'yinchoq avtomobildan iborat sovg'a to'plami.",
        "price": "529000.00",
        "stock_quantity": 15,
    },
    {
        "category": "Bolalar mahsulotlari",
        "name": "Play-Doh Kitchen Creations",
        "description": "Bolalar uchun oshxona mavzusidagi plastilin va aksessuarlar to'plami.",
        "price": "349000.00",
        "stock_quantity": 22,
    },
    {
        "category": "Bolalar mahsulotlari",
        "name": "Fisher-Price Laugh & Learn Smart Stages Chair",
        "description": "Musiqa, so'zlar va interaktiv tugmalar bilan rivojlantiruvchi stulcha.",
        "price": "899000.00",
        "stock_quantity": 8,
    },
    {
        "category": "Klaviatura va sichqonchalar",
        "name": "Logitech MX Master 3S",
        "description": "Ergonomik dizayn, jim tugmalar va yuqori aniqlikdagi sensorli sichqoncha.",
        "price": "1390000.00",
        "stock_quantity": 14,
    },
    {
        "category": "Klaviatura va sichqonchalar",
        "name": "Logitech MX Keys S",
        "description": "Past profilli, yoritgichli, ko'p qurilmaga ulanadigan simsiz klaviatura.",
        "price": "1650000.00",
        "stock_quantity": 9,
    },
    {
        "category": "Klaviatura va sichqonchalar",
        "name": "Keychron K2 Pro",
        "description": "Hot-swap mexanik switchlar va Bluetooth ulanishli kompakt klaviatura.",
        "price": "1290000.00",
        "stock_quantity": 12,
    },
    {
        "category": "Klaviatura va sichqonchalar",
        "name": "Razer DeathAdder V3",
        "description": "Yengil korpusli, aniq sensorli gaming sichqoncha.",
        "price": "1099000.00",
        "stock_quantity": 10,
    },
    {
        "category": "Klaviatura va sichqonchalar",
        "name": "Anker 737 Power Bank",
        "description": "24000 mAh sig'imli, USB-C Power Delivery bilan kuchli tashqi akkumulyator.",
        "price": "1990000.00",
        "stock_quantity": 7,
    },
    {
        "category": "Monitorlar",
        "name": "Dell UltraSharp U2723QE",
        "description": "27 dyuym 4K IPS Black panel va USB-C hubga ega professional monitor.",
        "price": "7990000.00",
        "stock_quantity": 5,
    },
    {
        "category": "Monitorlar",
        "name": "LG UltraGear 27GP850-B",
        "description": "27 dyuym QHD, 165 Hz yangilanish chastotali gaming monitor.",
        "price": "4990000.00",
        "stock_quantity": 6,
    },
    {
        "category": "Monitorlar",
        "name": "Samsung Smart Monitor M8 32",
        "description": "32 dyuym 4K smart monitor, Wi-Fi va streaming ilovalari bilan.",
        "price": "6690000.00",
        "stock_quantity": 4,
    },
    {
        "category": "Monitorlar",
        "name": "ASUS ProArt PA278QV",
        "description": "Dizayn va foto tahrirlash uchun 27 dyuym WQHD professional monitor.",
        "price": "4390000.00",
        "stock_quantity": 7,
    },
]


def _find_category_by_name(name: str) -> Category | None:
    return database.execute(select(Category).where(Category.name == name)).scalars().first()


def _find_product_by_name(name: str) -> Product | None:
    return database.execute(select(Product).where(Product.name == name)).scalars().first()


def _product_photo_path(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"images/products/{slug}.jpg"


def seed() -> tuple[int, int, int, int]:
    configure_file_storage()
    database.create_all()

    created_categories = 0
    updated_categories = 0
    created_products = 0
    updated_products = 0
    categories_by_name: dict[str, Category] = {}

    try:
        # First pass: create/update all categories
        for category_data in CATEGORIES:
            name = category_data["name"]
            parent_name = category_data.get("parent")

            category = _find_category_by_name(name)
            if category is None:
                category = Category(name=name)
                database.add(category)
                created_categories += 1
            else:
                updated_categories += 1

            category.description = category_data.get("description")
            categories_by_name[name] = category
        
        database.flush()

        # Second pass: set parent relationships
        for category_data in CATEGORIES:
            name = category_data["name"]
            parent_name = category_data.get("parent")
            parent = categories_by_name.get(parent_name) if parent_name else None
            
            category = categories_by_name[name]
            category.parent = parent
        
        database.flush()

        # Third pass: create/update products
        for product_data in PRODUCTS:
            category = categories_by_name[product_data["category"]]
            product = _find_product_by_name(product_data["name"])

            if product is None:
                product = Product(name=product_data["name"])
                database.add(product)
                created_products += 1
            else:
                updated_products += 1

            product.category = category
            product.photo = None  # Skip photo assignment during seeding
            product.description = product_data["description"]
            product.price = Decimal(product_data["price"])
            product.stock_quantity = product_data["stock_quantity"]
            product.is_active = True

        database.commit()
    except Exception:
        database.rollback()
        raise

    return created_categories, updated_categories, created_products, updated_products


if __name__ == "__main__":
    result = seed()
    print(
        "Seed completed: "
        f"{result[0]} categories created, {result[1]} categories updated, "
        f"{result[2]} products created, {result[3]} products updated."
    )
