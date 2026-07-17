import csv
from io import StringIO
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, models
from django.utils import timezone
from decimal import Decimal
from catalogo.models import (
    Categoria,
    Ingrediente,
    Receta,
    RecetaCategoria,
    RecetaIngrediente,
    HistorialPrecioIngrediente
)

# Categorías definidas en el PRD sección 11.1
CATEGORIAS_RAW = [
    ('DESAYUNO', 'Desayuno', 'desayuno'),
    ('ALMUERZO', 'Almuerzo', 'almuerzo'),
    ('CENA', 'Cena', 'cena'),
    ('ACOMPANAMIENTO', 'Acompañamiento', 'acompanamiento'),
    ('SOPA', 'Sopa', 'sopa'),
    ('POSTRE', 'Postre', 'postre'),
    ('MERIENDA', 'Merienda', 'merienda'),
]

# Ingredientes definidos en el PRD sección 11.2 (55 registros)
# Formato CSV: id, nombre, categoria_nutricional, unidad_medida, origen, nivel_costo, temporada
INGREDIENTES_RAW = """I001,Harina de maíz precocida,CER,gramos,NAC,ME,TODO
I002,Arroz,CER,gramos,NAC,ME,TODO
I003,Pasta,CER,gramos,IMP,ME,TODO
I004,Harina de trigo,CER,gramos,IMP,ME,TODO
I005,Avena en hojuelas,CER,gramos,IMP,ME,TODO
I006,Caraotas negras secas,LEG,gramos,NAC,ME,TODO
I007,Lentejas secas,LEG,gramos,IMP,ME,TODO
I008,Frijoles secos,LEG,gramos,NAC,ME,TODO
I009,Arvejas secas,LEG,gramos,IMP,ME,TODO
I010,Garbanzos secos,LEG,gramos,IMP,ME,TODO
I011,Papa,TUB,gramos,NAC,ME,TODO
I012,Yuca,TUB,gramos,NAC,ME,TODO
I013,Auyama,TUB,gramos,NAC,ME,TODO
I014,Plátano maduro,TUB,unidad,NAC,ME,TODO
I015,Plátano verde,TUB,unidad,NAC,ME,TODO
I016,Cebolla,VEG,unidad,NAC,ME,TODO
I017,Tomate,VEG,unidad,NAC,ME,TODO
I018,Ají dulce,VEG,unidad,NAC,ME,TODO
I019,Pimentón,VEG,unidad,NAC,ME,TODO
I020,Zanahoria,VEG,unidad,NAC,ME,TODO
I021,Repollo,VEG,unidad,NAC,ME,TODO
I022,Espinaca,VEG,gramos,NAC,ME,TODO
I023,Berenjena,VEG,unidad,NAC,ME,TODO
I024,Apio rama,VEG,unidad,NAC,ME,TODO
I025,Aguacate,FRU,unidad,NAC,ME,VERANO
I026,Limón,FRU,unidad,NAC,ME,TODO
I027,Jojoto maíz tierno,FRU,unidad,NAC,EM,VERANO
I028,Pollo en presas,PRA,gramos,NAC,EM,TODO
I029,Pechuga de pollo,PRA,gramos,NAC,EM,TODO
I030,Pollo entero,PRA,gramos,NAC,EM,TODO
I031,Pescado en filetes,PRA,gramos,NAC,EM,TODO
I032,Pescado de río,PRA,gramos,NAC,EM,TODO
I033,Hígado de res,PRA,gramos,NAC,ME,TODO
I034,Sardinas en agua lata,PRA,gramos,IMP,ME,TODO
I035,Huevos,HUE,unidad,NAC,ME,TODO
I036,Queso blanco,LAC,gramos,NAC,EM,TODO
I037,Queso de mano,LAC,gramos,NAC,EM,TODO
I038,Leche líquida,LAC,ml,NAC,EM,TODO
I039,Mantequilla,LAC,gramos,NAC,EM,TODO
I040,Aceite vegetal,GRA,ml,NAC,ME,TODO
I041,Sal,CON,gramos,NAC,ME,TODO
I042,Pimienta,CON,gramos,IMP,ME,TODO
I043,Ajo,CON,diente,NAC,ME,TODO
I044,Comino,CON,gramos,IMP,ME,TODO
I045,Orégano,CON,gramos,IMP,ME,TODO
I046,Canela,CON,gramos,IMP,ME,TODO
I047,Vinagre,CON,ml,NAC,ME,TODO
I048,Salsa de tomate,CON,gramos,NAC,ME,TODO
I049,Cilantro,HIE,manojo,NAC,ME,TODO
I050,Perejil,HIE,manojo,NAC,ME,TODO
I051,Cebollín,HIE,manojo,NAC,ME,TODO
I052,Papelón,EDU,gramos,NAC,ME,TODO
I053,Azúcar,EDU,gramos,NAC,ME,TODO
I054,Agua,LIQ,ml,NAC,NA,TODO
I055,Caldo de pollo,LIQ,ml,NAC,ME,TODO"""

# Recetas definidas en el PRD sección 11.3 (35 registros)
# Formato: codigo | nombre | categorias (separadas por +) | porciones | nivel_costo | kcal | prot | carb | gras | fibra | veg | vgn | sg | sl | ingredientes (separados por +)
RECETAS_RAW = """R001|Arepas asadas básicas|DESAYUNO+CENA|4|ME|280|9|52|4|5|S|N|S|N|I001+I054+I041+I036
R002|Perico / Revuelto|DESAYUNO|4|ME|180|12|6|12|2|S|N|S|S|I035+I017+I016+I018+I040+I041
R003|Arepas asadas integrales con auyama|DESAYUNO+CENA|4|ME|260|7|50|3|7|S|S|S|S|I001+I013+I054+I041
R004|Huevos sancochados con aguacate|DESAYUNO|4|ME|220|13|8|16|5|S|N|S|S|I035+I025+I017+I026+I041+I042
R005|Avena con papelón y canela|DESAYUNO|4|ME|200|6|38|3|4|S|S|N|S|I005+I054+I052+I046
R006|Cachapas con queso|DESAYUNO+CENA|4|EM|340|14|48|11|4|S|N|S|N|I027+I053+I041+I039+I037
R007|Caraotas negras guisadas|ALMUERZO+ACOMPANAMIENTO|6|ME|220|13|38|1|12|S|S|S|S|I006+I016+I018+I043+I044+I052+I041
R008|Lentejas guisadas|ALMUERZO|6|ME|240|14|40|2|11|S|S|S|S|I007+I016+I018+I043+I020+I044+I049
R009|Frijoles guisados|ALMUERZO|6|ME|230|13|39|1|11|S|S|S|S|I008+I016+I018+I043+I044+I049+I041
R010|Arvejas guisadas|ALMUERZO|6|ME|210|12|36|1|10|S|S|S|S|I009+I016+I018+I043+I020+I044+I049
R011|Garbanzos con espinaca y arroz|ALMUERZO|4|ME|380|14|65|6|10|S|S|S|S|I010+I022+I002+I016+I043+I040+I044+I041
R012|Arroz con caraotas|ALMUERZO|6|ME|290|11|56|2|8|S|S|S|S|I002+I006+I016+I043+I018+I044
R013|Pabellón económico sin carne|ALMUERZO|4|ME|410|14|78|6|11|S|S|S|S|I006+I002+I014+I040
R014|Sardinas guisadas|ALMUERZO|4|ME|240|22|8|13|2|N|N|S|S|I034+I016+I017+I018+I043+I049
R015|Huevos guisados con tomate|ALMUERZO+CENA|4|ME|200|13|8|13|2|S|N|S|S|I035+I017+I016+I018+I043+I041
R016|Tortilla de papa|CENA+DESAYUNO|4|ME|280|11|28|14|3|S|N|S|S|I011+I035+I016+I040+I041
R017|Yuca guisada con huevo|ALMUERZO|4|ME|290|9|50|7|4|S|N|S|S|I012+I035+I016+I018+I043+I049+I041
R018|Pasticho de berenjena|ALMUERZO|6|EM|340|15|38|14|6|S|N|N|N|I003+I023+I048+I036+I038+I004+I039
R019|Pasta con salsa de tomate casera|ALMUERZO+CENA|4|ME|320|11|58|6|5|S|N|N|N|I003+I017+I016+I043+I036+I040+I041+I045
R020|Pollo guisado en presas pequeñas|ALMUERZO|6|EM|310|28|10|18|2|N|N|S|S|I028+I016+I017+I018+I043+I044
R021|Pollo a la plancha con hierbas|ALMUERZO+CENA|4|EM|220|32|2|9|0|N|N|S|S|I029+I043+I045+I044+I026+I041+I042
R022|Pollo sancochado con verduras|ALMUERZO+SOPA|6|EM|260|26|18|9|4|N|N|S|S|I030+I020+I024+I051+I049+I043+I041
R023|Pescado a la plancha con limón|ALMUERZO|4|EM|200|28|2|9|0|N|N|S|S|I031+I026+I043+I041+I042+I040
R024|Pescado de río guisado|ALMUERZO|4|EM|240|26|8|12|2|N|N|S|S|I032+I016+I018+I017+I043+I049+I026
R025|Hígado encebollado|ALMUERZO|4|ME|230|26|8|10|1|N|N|S|S|I033+I016+I043+I040+I041+I042
R026|Arroz blanco|ACOMPANAMIENTO|4|ME|200|4|44|1|1|S|S|S|S|I002+I054+I040+I041
R027|Yuca sancochada|ACOMPANAMIENTO|4|ME|160|1|38|0|2|S|S|S|S|I012+I054+I041
R028|Plátano sancochado|ACOMPANAMIENTO+DESAYUNO|4|ME|170|2|40|0|3|S|S|S|S|I014+I054+I041
R029|Auyama horneada|ACOMPANAMIENTO|4|ME|110|2|22|2|4|S|S|S|S|I013+I043+I045+I040+I041+I042
R030|Ensalada de aguacate y tomate|ACOMPANAMIENTO|4|ME|160|2|12|12|6|S|S|S|S|I025+I017+I016+I049+I026+I040+I041
R031|Ensalada de repollo y zanahoria|ACOMPANAMIENTO|4|ME|70|2|12|2|4|S|S|S|S|I021+I020+I026+I040+I041
R032|Guasacaca|ACOMPANAMIENTO|6|ME|120|1|6|11|4|S|S|S|S|I025+I016+I018+I049+I050+I047+I040+I043+I041
R033|Pisca andina|SOPA+DESAYUNO|4|ME|240|14|24|10|3|S|N|S|N|I011+I038+I036+I035+I051+I049+I039
R034|Crema de auyama|SOPA|4|ME|140|4|22|5|4|S|N|S|N|I013+I016+I043+I055+I038+I039+I041
R035|Sopa de auyama y papa|SOPA+CENA|6|ME|130|3|28|1|4|S|S|S|S|I013+I011+I016+I043+I049+I041"""


class Command(BaseCommand):
    """
    Comando de gestión personalizado para cargar el catálogo base de Cocina Soberana.
    Garantiza idempotencia y valida que los ingredientes requeridos por las recetas existan.
    """
    help = 'Pobla la base de datos con el catálogo inicial de categorías, ingredientes y recetas del PRD.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-input',
            action='store_true',
            dest='no_input',
            help='Ejecuta la carga sin confirmación interactiva.',
        )

    def handle(self, *args, **options):
        # 1. Confirmación de limpieza de datos si no se pasa --no-input
        if not options['no_input']:
            self.stdout.write(self.style.WARNING(
                "ADVERTENCIA: Este comando eliminará las recetas, ingredientes y categorías existentes "
                "para realizar una carga limpia."
                "\nSi hay menús semanales o listas de compras guardados por usuarios, "
                "la operación fallará para proteger la integridad referencial."
            ))
            confirm = input("¿Confirmas que deseas limpiar y repoblar el catálogo? [s/N]: ")
            if confirm.lower() != 's':
                self.stdout.write(self.style.ERROR("Carga abortada por el usuario."))
                return

        self.stdout.write("Iniciando poblamiento de catálogo...")

        try:
            with transaction.atomic():
                # 2. Limpieza de tablas (relaciones primero, luego entidades maestras)
                self.stdout.write("Limpiando datos del catálogo...")
                RecetaCategoria.objects.all().delete()
                RecetaIngrediente.objects.all().delete()
                HistorialPrecioIngrediente.objects.all().delete()
                Receta.objects.all().delete()
                Ingrediente.objects.all().delete()
                Categoria.objects.all().delete()

                # 3. Creación de Categorías
                self.stdout.write("Cargando categorías...")
                categorias_db = {}
                for key, nombre, slug in CATEGORIAS_RAW:
                    cat = Categoria.objects.create(nombre=nombre, slug=slug)
                    categorias_db[key] = cat

                # 4. Creación de Ingredientes
                self.stdout.write("Cargando ingredientes...")
                ingredientes_db = {}
                csv_reader = csv.reader(StringIO(INGREDIENTES_RAW))
                
                for row in csv_reader:
                    if not row:
                        continue
                    ing_id, nombre, cat_nut, unidad, origen, nivel_costo, temporada = row
                    
                    ing = Ingrediente.objects.create(
                        nombre=nombre,
                        categoria_nutricional=cat_nut,
                        unidad_medida=unidad,
                        origen=origen,
                        nivel_costo=nivel_costo,
                        temporada=temporada,
                        precio_actual=Decimal('0.00'),
                        fecha_precio=None
                    )
                    
                    # Crear registro inicial de precio en 0.00 para gatillar el signal
                    HistorialPrecioIngrediente.objects.create(
                        fk_ingrediente=ing,
                        precio=Decimal('0.00'),
                        fecha=timezone.now().date()
                    )
                    
                    ingredientes_db[ing_id] = ing

                # 5. Creación de Recetas y sus relaciones
                self.stdout.write("Cargando recetas...")
                total_receta_categorias = 0
                total_receta_ingredientes = 0
                
                # Procesar recetas línea por línea
                for line in RECETAS_RAW.strip().split('\n'):
                    if not line:
                        continue
                    parts = [p.strip() for p in line.split('|')]
                    
                    (
                        codigo,
                        nombre,
                        cats_str,
                        porciones,
                        nivel_costo,
                        kcal,
                        prot,
                        carb,
                        gras,
                        fibra,
                        veg,
                        vgn,
                        sg,
                        sl,
                        ings_str
                    ) = parts

                    # Parsear banderas S/N
                    es_veg = veg == 'S'
                    es_vgn = vgn == 'S'
                    es_sg = sg == 'S'
                    es_sl = sl == 'S'

                    # Crear Receta
                    receta = Receta.objects.create(
                        codigo=codigo,
                        nombre=nombre,
                        porciones_base=int(porciones),
                        calorias_por_porcion=int(kcal),
                        proteinas_g=Decimal(prot),
                        carbohidratos_g=Decimal(carb),
                        grasas_g=Decimal(gras),
                        fibra_g=Decimal(fibra),
                        nivel_costo=nivel_costo,
                        es_vegetariana=es_veg,
                        es_vegana=es_vgn,
                        es_sin_gluten=es_sg,
                        es_sin_lactosa=es_sl
                    )

                    # Relaciones con Categorías (DESAYUNO+CENA...)
                    for cat_key in cats_str.split('+'):
                        cat_key = cat_key.strip()
                        if cat_key in categorias_db:
                            RecetaCategoria.objects.create(
                                fk_receta=receta,
                                fk_categoria=categorias_db[cat_key]
                            )
                            total_receta_categorias += 1
                        else:
                            raise CommandError(
                                f"La categoría '{cat_key}' de la receta '{codigo}' no está definida base."
                            )

                    # Relaciones con Ingredientes (I001+I054...)
                    for ing_key in ings_str.split('+'):
                        ing_key = ing_key.strip()
                        if ing_key in ingredientes_db:
                            RecetaIngrediente.objects.create(
                                fk_receta=receta,
                                fk_ingrediente=ingredientes_db[ing_key],
                                cantidad=None,  # Curation pending for v1
                                nota_uso=""
                            )
                            total_receta_ingredientes += 1
                        else:
                            raise CommandError(
                                f"El ingrediente '{ing_key}' referenciado en la receta '{codigo}' "
                                f"no existe en el catálogo."
                            )

            # Reporte de conteos
            num_categorias = Categoria.objects.count()
            num_ingredientes = Ingrediente.objects.count()
            num_recetas = Receta.objects.count()

            self.stdout.write(self.style.SUCCESS(
                f"Carga finalizada con éxito:"
                f"\n- {num_categorias} categorías"
                f"\n- {num_ingredientes} ingredientes"
                f"\n- {num_recetas} recetas"
                f"\n- {total_receta_ingredientes} RecetaIngrediente"
                f"\n- {total_receta_categorias} RecetaCategoria"
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error durante la carga: {str(e)}"))
            raise e
