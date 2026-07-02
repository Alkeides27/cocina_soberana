import sys
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from catalogo.models import Receta, Ingrediente, RecetaIngrediente

CANTIDADES_RECETAS = [
    {
        "codigo_receta": "R001",
        "notas_preparacion": "Mezclar harina con agua tibia y sal hasta obtener masa suave. Formar bolas y aplastar en discos de ~1 cm de grosor. Asar en budare o sartén caliente sin aceite, 5 minutos por lado. Abrir y rellenar con queso.",
        "ingredientes": [
            {"ingrediente_nombre": "Harina de maíz precocida", "cantidad": 500},
            {"ingrediente_nombre": "Agua", "cantidad": 600},
            {"ingrediente_nombre": "Sal", "cantidad": 5},
            {"ingrediente_nombre": "Queso blanco", "cantidad": 300},
        ]
    },
    {
        "codigo_receta": "R002",
        "notas_preparacion": "Sofreír cebolla, tomate y ají picados finos en aceite hasta que ablanden. Agregar huevos batidos con sal y revolver hasta que cuajen sin secarse.",
        "ingredientes": [
            {"ingrediente_nombre": "Huevos", "cantidad": 8},
            {"ingrediente_nombre": "Tomate", "cantidad": 2},
            {"ingrediente_nombre": "Cebolla", "cantidad": 1},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 4},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 30},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
        ]
    },
    {
        "codigo_receta": "R003",
        "notas_preparacion": "Mezclar harina con auyama triturada (previamente cocida y enfriada), agregar agua tibia y sal. Amasar hasta obtener consistencia uniforme. Formar y asar igual que las arepas básicas.",
        "ingredientes": [
            {"ingrediente_nombre": "Harina de maíz precocida", "cantidad": 400},
            {"ingrediente_nombre": "Auyama", "cantidad": 200},
            {"ingrediente_nombre": "Agua", "cantidad": 500},
            {"ingrediente_nombre": "Sal", "cantidad": 5},
        ]
    },
    {
        "codigo_receta": "R004",
        "notas_preparacion": "Hervir huevos 10 minutos. Pelar y partir en mitades. Servir con aguacate y tomate en cubos, jugo de limón y sal.",
        "ingredientes": [
            {"ingrediente_nombre": "Huevos", "cantidad": 8},
            {"ingrediente_nombre": "Aguacate", "cantidad": 2},
            {"ingrediente_nombre": "Tomate", "cantidad": 1},
            {"ingrediente_nombre": "Limón", "cantidad": 1},
            {"ingrediente_nombre": "Sal", "cantidad": 2},
        ]
    },
    {
        "codigo_receta": "R007",
        "notas_preparacion": "Remojar caraotas en agua durante la noche anterior. Cocinar en olla con agua nueva hasta ablandar (~1 hora). Aparte, sofreír cebolla, ají y ajo en aceite, agregar comino. Incorporar al guiso, añadir papelón y sal, cocinar 15 minutos más.",
        "ingredientes": [
            {"ingrediente_nombre": "Caraotas negras secas", "cantidad": 500},
            {"ingrediente_nombre": "Cebolla", "cantidad": 1},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 3},
            {"ingrediente_nombre": "Ajo", "cantidad": 3},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 30},
            {"ingrediente_nombre": "Comino", "cantidad": 5},
            {"ingrediente_nombre": "Papelón", "cantidad": 20},
            {"ingrediente_nombre": "Sal", "cantidad": 5},
        ]
    },
    {
        "codigo_receta": "R008",
        "notas_preparacion": "Lavar las lentejas. Cocinar en agua hasta ablandar (~30 minutos). Sofreír cebolla, ají, ajo, zanahoria picada. Agregar al guiso con comino y sal. Cocinar 15 minutos más, terminar con cilantro picado.",
        "ingredientes": [
            {"ingrediente_nombre": "Lentejas secas", "cantidad": 500},
            {"ingrediente_nombre": "Cebolla", "cantidad": 1},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 3},
            {"ingrediente_nombre": "Ajo", "cantidad": 3},
            {"ingrediente_nombre": "Zanahoria", "cantidad": 1},
            {"ingrediente_nombre": "Comino", "cantidad": 5},
            {"ingrediente_nombre": "Cilantro", "cantidad": 1},
            {"ingrediente_nombre": "Sal", "cantidad": 5},
        ]
    },
    {
        "codigo_receta": "R009",
        "notas_preparacion": "",
        "ingredientes": [
            {"ingrediente_nombre": "Frijoles secos", "cantidad": 500},
            {"ingrediente_nombre": "Cebolla", "cantidad": 1},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 3},
            {"ingrediente_nombre": "Ajo", "cantidad": 3},
            {"ingrediente_nombre": "Comino", "cantidad": 5},
            {"ingrediente_nombre": "Cilantro", "cantidad": 1},
            {"ingrediente_nombre": "Sal", "cantidad": 5},
        ]
    },
    {
        "codigo_receta": "R012",
        "notas_preparacion": "Cocinar las caraotas previamente. Sofreír el aliño en aceite, agregar el arroz, las caraotas con un poco de su caldo y agua hasta cubrir. Cocinar a fuego bajo hasta que el arroz absorba el líquido.",
        "ingredientes": [
            {"ingrediente_nombre": "Arroz", "cantidad": 400},
            {"ingrediente_nombre": "Caraotas negras secas", "cantidad": 200},
            {"ingrediente_nombre": "Cebolla", "cantidad": 1},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 2},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Comino", "cantidad": 3},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 30},
            {"ingrediente_nombre": "Sal", "cantidad": 5},
        ]
    },
    {
        "codigo_receta": "R013",
        "notas_preparacion": "Servir en plato individual: porción de arroz, porción de caraotas, plátano asado al horno cortado en tajadas. Es un pabellón sin la carne mechada — versión accesible que mantiene el balance proteína (caraotas) + carbohidrato (arroz) + dulce (plátano).",
        "ingredientes": [
            {"ingrediente_nombre": "Caraotas negras secas", "cantidad": 400},
            {"ingrediente_nombre": "Arroz", "cantidad": 400},
            {"ingrediente_nombre": "Plátano maduro", "cantidad": 2},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 15},
        ]
    },
    {
        "codigo_receta": "R015",
        "notas_preparacion": "",
        "ingredientes": [
            {"ingrediente_nombre": "Huevos", "cantidad": 8},
            {"ingrediente_nombre": "Tomate", "cantidad": 3},
            {"ingrediente_nombre": "Cebolla", "cantidad": 1},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 3},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 15},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
        ]
    },
    {
        "codigo_receta": "R017",
        "notas_preparacion": "",
        "ingredientes": [
            {"ingrediente_nombre": "Yuca", "cantidad": 500},
            {"ingrediente_nombre": "Huevos", "cantidad": 4},
            {"ingrediente_nombre": "Cebolla", "cantidad": 1},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 2},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Cilantro", "cantidad": 0.5},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
        ]
    },
    {
        "codigo_receta": "R020",
        "notas_preparacion": "Salpimentar el pollo. Sofreír cebolla, tomate, ají y ajo. Agregar el pollo, dorar por todos lados. Añadir un poco de agua, comino y sal. Cocinar a fuego medio-bajo tapado durante 30-40 minutos hasta que el pollo esté tierno y la salsa se concentre.",
        "ingredientes": [
            {"ingrediente_nombre": "Pollo en presas", "cantidad": 1000},
            {"ingrediente_nombre": "Cebolla", "cantidad": 2},
            {"ingrediente_nombre": "Tomate", "cantidad": 2},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 4},
            {"ingrediente_nombre": "Ajo", "cantidad": 4},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 30},
            {"ingrediente_nombre": "Comino", "cantidad": 5},
            {"ingrediente_nombre": "Sal", "cantidad": 5},
        ]
    },
    {
        "codigo_receta": "R025",
        "notas_preparacion": "",
        "ingredientes": [
            {"ingrediente_nombre": "Hígado de res", "cantidad": 500},
            {"ingrediente_nombre": "Cebolla", "cantidad": 2},
            {"ingrediente_nombre": "Ajo", "cantidad": 3},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 30},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
            {"ingrediente_nombre": "Pimienta", "cantidad": 2},
        ]
    },
    {
        "codigo_receta": "R026",
        "notas_preparacion": "Lavar el arroz hasta que el agua salga clara. En olla, llevar a hervor el agua con sal y aceite. Agregar arroz, bajar fuego al mínimo, tapar y cocinar 18-20 minutos sin destapar. Reposar 5 minutos.",
        "ingredientes": [
            {"ingrediente_nombre": "Arroz", "cantidad": 400},
            {"ingrediente_nombre": "Agua", "cantidad": 800},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 15},
            {"ingrediente_nombre": "Sal", "cantidad": 5},
        ]
    },
    {
        "codigo_receta": "R027",
        "notas_preparacion": "",
        "ingredientes": [
            {"ingrediente_nombre": "Yuca", "cantidad": 800},
            {"ingrediente_nombre": "Agua", "cantidad": 1000},
            {"ingrediente_nombre": "Sal", "cantidad": 5},
        ]
    },
    {
        "codigo_receta": "R028",
        "notas_preparacion": "",
        "ingredientes": [
            {"ingrediente_nombre": "Plátano maduro", "cantidad": 4},
            {"ingrediente_nombre": "Agua", "cantidad": 1000},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
        ]
    },
    {
        "codigo_receta": "R030",
        "notas_preparacion": "Cortar aguacate y tomate en cubos. Picar cebolla muy fina y cilantro. Mezclar con jugo de limón, aceite y sal. Servir frío.",
        "ingredientes": [
            {"ingrediente_nombre": "Aguacate", "cantidad": 2},
            {"ingrediente_nombre": "Tomate", "cantidad": 3},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Cilantro", "cantidad": 0.5},
            {"ingrediente_nombre": "Limón", "cantidad": 1},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 15},
            {"ingrediente_nombre": "Sal", "cantidad": 2},
        ]
    },
    {
        "codigo_receta": "R031",
        "notas_preparacion": "",
        "ingredientes": [
            {"ingrediente_nombre": "Repollo", "cantidad": 0.5},
            {"ingrediente_nombre": "Zanahoria", "cantidad": 2},
            {"ingrediente_nombre": "Limón", "cantidad": 1},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 15},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
        ]
    },
    {
        "codigo_receta": "R034",
        "notas_preparacion": "Sofreír cebolla y ajo en mantequilla. Agregar auyama en cubos y agua/caldo. Cocinar hasta que ablanden. Procesar con leche hasta obtener crema lisa. Ajustar sal y pimienta.",
        "ingredientes": [
            {"ingrediente_nombre": "Auyama", "cantidad": 1000},
            {"ingrediente_nombre": "Cebolla", "cantidad": 1},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Caldo de pollo", "cantidad": 1000},
            {"ingrediente_nombre": "Leche líquida", "cantidad": 200},
            {"ingrediente_nombre": "Mantequilla", "cantidad": 30},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
            {"ingrediente_nombre": "Pimienta", "cantidad": 1},
        ]
    },
    {
        "codigo_receta": "R035",
        "notas_preparacion": "",
        "ingredientes": [
            {"ingrediente_nombre": "Auyama", "cantidad": 600},
            {"ingrediente_nombre": "Papa", "cantidad": 400},
            {"ingrediente_nombre": "Cebolla", "cantidad": 1},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Cilantro", "cantidad": 0.5},
            {"ingrediente_nombre": "Sal", "cantidad": 5},
        ]
    }
]

class Command(BaseCommand):
    help = 'Actualiza las cantidades y notas de preparación curadas para las 20 recetas iniciales.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra las acciones que se realizarían sin modificar la base de datos.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING("EJECUCIÓN EN MODO DRY-RUN: No se guardarán cambios."))

        recetas_procesadas = 0
        ingredientes_actualizados = 0
        ingredientes_faltantes = 0
        
        try:
            with transaction.atomic():
                for datos in CANTIDADES_RECETAS:
                    codigo = datos["codigo_receta"]
                    try:
                        receta = Receta.objects.get(codigo=codigo)
                    except Receta.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Receta {codigo} no encontrada. Saltando."))
                        continue
                    
                    if not receta.notas_preparacion and datos["notas_preparacion"]:
                        receta.notas_preparacion = datos["notas_preparacion"]
                        if not dry_run:
                            receta.save(update_fields=['notas_preparacion'])
                        self.stdout.write(f"  - Notas actualizadas para {codigo}")
                    
                    self.stdout.write(self.style.SUCCESS(f"Procesando receta: {receta.codigo} - {receta.nombre}"))
                    recetas_procesadas += 1
                    
                    for ing_data in datos["ingredientes"]:
                        ing_nombre = ing_data["ingrediente_nombre"]
                        cantidad = Decimal(str(ing_data["cantidad"]))
                        
                        try:
                            ingrediente = Ingrediente.objects.get(nombre__iexact=ing_nombre)
                        except Ingrediente.DoesNotExist:
                            self.stdout.write(self.style.WARNING(f"  [!] Ingrediente '{ing_nombre}' no encontrado. Saltando."))
                            ingredientes_faltantes += 1
                            continue
                            
                        ri, created = RecetaIngrediente.objects.get_or_create(
                            fk_receta=receta,
                            fk_ingrediente=ingrediente,
                            defaults={'cantidad': cantidad}
                        )
                        
                        if not created:
                            ri.cantidad = cantidad
                            if not dry_run:
                                ri.save(update_fields=['cantidad'])
                                
                        ingredientes_actualizados += 1
                        accion = "Creado" if created else "Actualizado"
                        self.stdout.write(f"  - {accion}: {ingrediente.nombre} = {cantidad}")
                
                if dry_run:
                    raise Exception("Rollback forzado por --dry-run")
                    
        except Exception as e:
            if dry_run and str(e) == "Rollback forzado por --dry-run":
                self.stdout.write(self.style.SUCCESS("Dry-run finalizado correctamente (cambios revertidos)."))
            else:
                self.stdout.write(self.style.ERROR(f"Error durante la carga: {e}"))
                raise
                
        # Resumen final
        self.stdout.write("\n" + "="*40)
        self.stdout.write(self.style.SUCCESS(f"RESUMEN DE OPERACIÓN {'(DRY-RUN)' if dry_run else ''}"))
        self.stdout.write(f"Recetas procesadas: {recetas_procesadas}")
        self.stdout.write(f"Ingredientes actualizados/creados: {ingredientes_actualizados}")
        if ingredientes_faltantes > 0:
            self.stdout.write(self.style.WARNING(f"Ingredientes no encontrados en BD: {ingredientes_faltantes}"))
        self.stdout.write("="*40 + "\n")
