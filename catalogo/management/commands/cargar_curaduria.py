import sys
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from catalogo.models import Receta, Ingrediente, RecetaIngrediente, HistorialPrecioIngrediente, Categoria

PRECIOS_REFERENCIA = {
    # ── Cereales (precio por kg) ──────────────────────────────────────────────
    "Harina de maíz precocida": Decimal('3.00'),   # NUEVO — $3/kg
    "Arroz": Decimal('2.50'),                       # era $1.29/kg
    "Pasta": Decimal('3.00'),                       # era $2.17/kg
    "Harina de trigo": Decimal('2.50'),             # era $1.07/kg
    "Avena en hojuelas": Decimal('3.50'),           # era $1.50/kg
    # ── Leguminosas (precio por kg) ───────────────────────────────────────────
    "Caraotas negras secas": Decimal('5.00'),       # NUEVO — $5/kg
    "Lentejas secas": Decimal('4.50'),              # NUEVO — $4.50/kg
    "Frijoles secos": Decimal('4.50'),              # NUEVO — $4.50/kg
    "Arvejas secas": Decimal('5.00'),               # era $1.29/kg
    "Garbanzos secos": Decimal('5.50'),             # era $2.33/kg
    # ── Tubérculos y plátanos (precio por kg, excepto plátano = por unidad) ──
    "Papa": Decimal('3.50'),                        # era $3.40/kg
    "Yuca": Decimal('2.50'),                        # NUEVO — $2.50/kg
    "Auyama": Decimal('2.00'),                      # era $0.97/kg
    "Plátano maduro": Decimal('0.80'),              # NUEVO — $0.80/unidad (~250g)
    "Plátano verde": Decimal('0.60'),               # NUEVO — $0.60/unidad
    # ── Vegetales (precio por kg) ─────────────────────────────────────────────
    "Cebolla": Decimal('3.50'),                     # era $1.81/kg
    "Tomate": Decimal('3.50'),                      # era $2.30/kg
    "Ají dulce": Decimal('5.00'),                   # era $0.76/kg  ← muy subvalorado
    "Pimentón": Decimal('5.00'),                    # NUEVO — $5/kg
    "Zanahoria": Decimal('3.00'),                   # era $1.50/kg
    "Repollo": Decimal('2.50'),                     # NUEVO — $2.50/kg
    "Espinaca": Decimal('6.00'),                    # era $3.00/kg
    "Berenjena": Decimal('3.00'),                   # era $1.44/kg
    "Apio rama": Decimal('3.00'),                   # era $1.22/kg
    # ── Frutas (precio por kg, jojoto = por unidad) ───────────────────────────
    "Aguacate": Decimal('8.00'),                    # era $4.19/kg
    "Limón": Decimal('4.00'),                       # era $1.54/kg
    "Jojoto maíz tierno": Decimal('0.75'),          # era $0.30/unidad
    # ── Proteína Animal (precio por kg) ───────────────────────────────────────
    "Pollo en presas": Decimal('5.50'),             # NUEVO — $5.50/kg
    "Pechuga de pollo": Decimal('9.00'),            # era $6.50/kg
    "Pollo entero": Decimal('5.00'),                # era $3.50/kg
    "Pescado en filetes": Decimal('10.00'),         # era $5.00/kg
    "Pescado de río": Decimal('7.00'),              # era $4.00/kg
    "Hígado de res": Decimal('7.00'),               # NUEVO — $7/kg
    "Sardinas en agua lata": Decimal('8.00'),       # era $1.59 → ahora $/kg correcto
    # ── Huevos (precio por medio cartón = 15 unidades) ────────────────────────
    "Huevos": Decimal('4.50'),                      # era $2.25; código divide por 15
    # ── Lácteos (queso y mantequilla = $/kg; leche = $/litro) ─────────────────
    "Queso blanco": Decimal('9.00'),                # era $2.80/kg
    "Queso de mano": Decimal('14.00'),              # era $6.00/kg
    "Leche líquida": Decimal('2.00'),               # era $3.10/L
    "Mantequilla": Decimal('6.00'),                 # era $1.60/kg
    # ── Grasas (precio por litro) ─────────────────────────────────────────────
    "Aceite vegetal": Decimal('5.00'),              # era $3.25/L
    # ── Condimentos (precio por kg) ───────────────────────────────────────────
    "Sal": Decimal('1.50'),                         # era $0.90/kg
    "Pimienta": Decimal('15.00'),                   # era $3.00/kg
    "Ajo": Decimal('10.00'),                        # era $1.69/kg  ← muy subvalorado
    "Comino": Decimal('15.00'),                     # era $0.80/kg
    "Orégano": Decimal('12.00'),                    # era $1.50/kg
    "Canela": Decimal('10.00'),                     # era $1.00/kg
    "Vinagre": Decimal('3.50'),                     # era $1.70/L
    "Salsa de tomate": Decimal('3.00'),             # era $1.50/kg
    # ── Hierbas (precio por kg; código multiplica × 0.05 para manojos) ────────
    "Cilantro": Decimal('5.00'),                    # era $1.36/kg
    "Perejil": Decimal('5.00'),                     # era $2.00/kg
    "Cebollín": Decimal('3.00'),                    # era $0.98/kg
    # ── Edulcorantes (precio por kg) ──────────────────────────────────────────
    "Papelón": Decimal('3.00'),                     # era $1.35/kg
    "Azúcar": Decimal('2.00'),                      # era $1.50/kg
    # ── Líquidos ──────────────────────────────────────────────────────────────
    "Agua": Decimal('0.00'),                        # agua corriente = gratis
    "Caldo de pollo": Decimal('2.00'),              # NUEVO — $2/litro
}

CANTIDADES_RECETAS = [
    {
        "codigo_receta": "R001",
        "notas_preparacion": "Mezclar harina con agua tibia y sal hasta obtener masa suave. Formar bolas y aplastar en discos de ~1 cm de grosor. Asar en budare o sartén caliente sin aceite, 5 minutos por lado. Abrir y rellenar con queso.",
        "ingredientes": [
            {"ingrediente_nombre": "Harina de maíz precocida", "cantidad": 250},
            {"ingrediente_nombre": "Agua", "cantidad": 300},
            {"ingrediente_nombre": "Sal", "cantidad": 5},
            {"ingrediente_nombre": "Queso blanco", "cantidad": 150},
        ]
    },
    {
        "codigo_receta": "R002",
        "notas_preparacion": "Sofreír cebolla, tomate y ají picados finos en aceite hasta que ablanden. Agregar huevos batidos con sal y revolver hasta que cuajen sin secarse.",
        "ingredientes": [
            {"ingrediente_nombre": "Huevos", "cantidad": 4},
            {"ingrediente_nombre": "Tomate", "cantidad": 1},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 2},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 15},
            {"ingrediente_nombre": "Sal", "cantidad": 2},
        ]
    },
    {
        "codigo_receta": "R003",
        "notas_preparacion": "Mezclar harina con auyama triturada (previamente cocida y enfriada), agregar agua tibia y sal. Amasar hasta obtener consistencia uniforme. Formar y asar igual que las arepas básicas.",
        "ingredientes": [
            {"ingrediente_nombre": "Harina de maíz precocida", "cantidad": 200},
            {"ingrediente_nombre": "Auyama", "cantidad": 150},
            {"ingrediente_nombre": "Agua", "cantidad": 250},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
        ]
    },
    {
        "codigo_receta": "R004",
        "notas_preparacion": "Hervir huevos 10 minutos. Pelar y partir en mitades. Servir con aguacate y tomate en cubos, jugo de limón y sal.",
        "ingredientes": [
            {"ingrediente_nombre": "Huevos", "cantidad": 4},
            {"ingrediente_nombre": "Aguacate", "cantidad": 1},
            {"ingrediente_nombre": "Tomate", "cantidad": 1},
            {"ingrediente_nombre": "Limón", "cantidad": 1},
            {"ingrediente_nombre": "Sal", "cantidad": 2},
        ]
    },
    {
        "codigo_receta": "R007",
        "notas_preparacion": "Remojar caraotas en agua durante la noche anterior. Cocinar en olla con agua nueva hasta ablandar (~1 hora). Aparte, sofreír cebolla, ají y ajo en aceite, agregar comino. Incorporar al guiso, añadir papelón y sal, cocinar 15 minutos más.",
        "ingredientes": [
            {"ingrediente_nombre": "Caraotas negras secas", "cantidad": 250},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 2},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 15},
            {"ingrediente_nombre": "Comino", "cantidad": 2},
            {"ingrediente_nombre": "Papelón", "cantidad": 10},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
        ]
    },
    {
        "codigo_receta": "R008",
        "notas_preparacion": "Lavar las lentejas. Cocinar en agua hasta ablandar (~30 minutos). Sofreír cebolla, ají, ajo, zanahoria picada. Agregar al guiso con comino y sal. Cocinar 15 minutos más, terminar con cilantro picado.",
        "ingredientes": [
            {"ingrediente_nombre": "Lentejas secas", "cantidad": 250},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 2},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Zanahoria", "cantidad": 1},
            {"ingrediente_nombre": "Comino", "cantidad": 2},
            {"ingrediente_nombre": "Cilantro", "cantidad": 0.25},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
        ]
    },
    {
        "codigo_receta": "R009",
        "notas_preparacion": "",
        "ingredientes": [
            {"ingrediente_nombre": "Frijoles secos", "cantidad": 250},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 2},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Comino", "cantidad": 2},
            {"ingrediente_nombre": "Cilantro", "cantidad": 0.25},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
        ]
    },
    {
        "codigo_receta": "R012",
        "notas_preparacion": "Cocinar las caraotas previamente. Sofreír el aliño en aceite, agregar el arroz, las caraotas con un poco de su caldo y agua hasta cubrir. Cocinar a fuego bajo hasta que el arroz absorba el líquido.",
        "ingredientes": [
            {"ingrediente_nombre": "Arroz", "cantidad": 250},
            {"ingrediente_nombre": "Caraotas negras secas", "cantidad": 150},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 1},
            {"ingrediente_nombre": "Ajo", "cantidad": 1},
            {"ingrediente_nombre": "Comino", "cantidad": 1},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 15},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
        ]
    },
    {
        "codigo_receta": "R013",
        "notas_preparacion": "Servir en plato individual: porción de arroz, porción de caraotas, plátano asado al horno cortado en tajadas. Es un pabellón sin la carne mechada — versión accesible que mantiene el balance proteína (caraotas) + carbohidrato (arroz) + dulce (plátano).",
        "ingredientes": [
            {"ingrediente_nombre": "Caraotas negras secas", "cantidad": 200},
            {"ingrediente_nombre": "Arroz", "cantidad": 250},
            {"ingrediente_nombre": "Plátano maduro", "cantidad": 1.5},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 10},
        ]
    },
    {
        "codigo_receta": "R015",
        "notas_preparacion": "",
        "ingredientes": [
            {"ingrediente_nombre": "Huevos", "cantidad": 4},
            {"ingrediente_nombre": "Tomate", "cantidad": 1.5},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 1.5},
            {"ingrediente_nombre": "Ajo", "cantidad": 1},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 10},
            {"ingrediente_nombre": "Sal", "cantidad": 2},
        ]
    },
    {
        "codigo_receta": "R017",
        "notas_preparacion": "",
        "ingredientes": [
            {"ingrediente_nombre": "Yuca", "cantidad": 350},
            {"ingrediente_nombre": "Huevos", "cantidad": 3},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 1},
            {"ingrediente_nombre": "Ajo", "cantidad": 1},
            {"ingrediente_nombre": "Cilantro", "cantidad": 0.25},
            {"ingrediente_nombre": "Sal", "cantidad": 2},
        ]
    },
    {
        "codigo_receta": "R020",
        "notas_preparacion": "Salpimentar el pollo. Sofreír cebolla, tomate, ají y ajo. Agregar el pollo, dorar por todos lados. Añadir un poco de agua, comino y sal. Cocinar a fuego medio-bajo tapado durante 30-40 minutos hasta que el pollo esté tierno y la salsa se concentre.",
        "ingredientes": [
            {"ingrediente_nombre": "Pollo en presas", "cantidad": 450},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Tomate", "cantidad": 1},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 2},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 15},
            {"ingrediente_nombre": "Comino", "cantidad": 2},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
        ]
    },
    {
        "codigo_receta": "R025",
        "notas_preparacion": "",
        "ingredientes": [
            {"ingrediente_nombre": "Hígado de res", "cantidad": 350},
            {"ingrediente_nombre": "Cebolla", "cantidad": 1},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 15},
            {"ingrediente_nombre": "Sal", "cantidad": 2},
            {"ingrediente_nombre": "Pimienta", "cantidad": 1},
        ]
    },
    {
        "codigo_receta": "R026",
        "notas_preparacion": "Lavar el arroz hasta que el agua salga clara. En olla, llevar a hervor el agua con sal y aceite. Agregar arroz, bajar fuego al mínimo, tapar y cocinar 18-20 minutos sin destapar. Reposar 5 minutos.",
        "ingredientes": [
            {"ingrediente_nombre": "Arroz", "cantidad": 250},
            {"ingrediente_nombre": "Agua", "cantidad": 500},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 10},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
        ]
    },
    {
        "codigo_receta": "R027",
        "notas_preparacion": "",
        "ingredientes": [
            {"ingrediente_nombre": "Yuca", "cantidad": 450},
            {"ingrediente_nombre": "Agua", "cantidad": 600},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
        ]
    },
    {
        "codigo_receta": "R028",
        "notas_preparacion": "",
        "ingredientes": [
            {"ingrediente_nombre": "Plátano maduro", "cantidad": 2},
            {"ingrediente_nombre": "Agua", "cantidad": 500},
            {"ingrediente_nombre": "Sal", "cantidad": 2},
        ]
    },
    {
        "codigo_receta": "R030",
        "notas_preparacion": "Cortar aguacate y tomate en cubos. Picar cebolla muy fina y cilantro. Mezclar con jugo de limón, aceite y sal. Servir frío.",
        "ingredientes": [
            {"ingrediente_nombre": "Aguacate", "cantidad": 1},
            {"ingrediente_nombre": "Tomate", "cantidad": 1.5},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.25},
            {"ingrediente_nombre": "Cilantro", "cantidad": 0.25},
            {"ingrediente_nombre": "Limón", "cantidad": 0.5},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 10},
            {"ingrediente_nombre": "Sal", "cantidad": 1},
        ]
    },
    {
        "codigo_receta": "R031",
        "notas_preparacion": "",
        "ingredientes": [
            {"ingrediente_nombre": "Repollo", "cantidad": 0.25},
            {"ingrediente_nombre": "Zanahoria", "cantidad": 1},
            {"ingrediente_nombre": "Limón", "cantidad": 0.5},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 10},
            {"ingrediente_nombre": "Sal", "cantidad": 2},
        ]
    },
    {
        "codigo_receta": "R034",
        "notas_preparacion": "Sofreír cebolla y ajo en mantequilla. Agregar auyama en cubos y agua/caldo. Cocinar hasta que ablanden. Procesar con leche hasta obtener crema lisa. Ajustar sal y pimienta.",
        "ingredientes": [
            {"ingrediente_nombre": "Auyama", "cantidad": 600},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Ajo", "cantidad": 1},
            {"ingrediente_nombre": "Caldo de pollo", "cantidad": 600},
            {"ingrediente_nombre": "Leche líquida", "cantidad": 120},
            {"ingrediente_nombre": "Mantequilla", "cantidad": 15},
            {"ingrediente_nombre": "Sal", "cantidad": 2},
            {"ingrediente_nombre": "Pimienta", "cantidad": 0.5},
        ]
    },
    {
        "codigo_receta": "R035",
        "notas_preparacion": "",
        "ingredientes": [
            {"ingrediente_nombre": "Auyama", "cantidad": 400},
            {"ingrediente_nombre": "Papa", "cantidad": 250},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Ajo", "cantidad": 1},
            {"ingrediente_nombre": "Cilantro", "cantidad": 0.25},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
        ]
    },
    {
        "codigo_receta": "R005",
        "notas_preparacion": "En una olla, vierte el agua junto con el papelón en trozos y las ramas de canela. Calienta a fuego medio hasta que el papelón se disuelva por completo e infusione el agua. Agrega la avena en hojuelas a la infusión. Reduce el fuego a bajo y cocina durante 8 a 10 minutos, removiendo constantemente con una cuchara de madera para evitar que se pegue al fondo. Una vez que obtengas una consistencia cremosa, retira las ramas de canela y sirve caliente o templada.",
        "ingredientes": [
            {"ingrediente_nombre": "Avena en hojuelas", "cantidad": 120},
            {"ingrediente_nombre": "Agua", "cantidad": 500},
            {"ingrediente_nombre": "Papelón", "cantidad": 30},
            {"ingrediente_nombre": "Canela", "cantidad": 1},
        ]
    },
    {
        "codigo_receta": "R006",
        "notas_preparacion": "Desgrana los jojotos y muele los granos (o lícualos a velocidad media-baja) junto con el azúcar, la sal y una cucharada de mantequilla derretida hasta obtener una mezcla espesa y ligeramente texturizada. Calienta un budare o sartén plano a fuego medio y úntalo con un toque de mantequilla. Vierte una porción de la mezcla en el centro formando un círculo de grosor medio. Cocina por unos 3 a 5 minutos hasta que se formen burbujas en la superficie, dale la vuelta y dora el otro lado. Retira la cachapa caliente, úntale un poco de mantequilla, colócale una rueda de queso de mano en el centro, dóblala a la mitad y sirve inmediatamente.",
        "ingredientes": [
            {"ingrediente_nombre": "Jojoto maíz tierno", "cantidad": 3},
            {"ingrediente_nombre": "Azúcar", "cantidad": 20},
            {"ingrediente_nombre": "Sal", "cantidad": 2},
            {"ingrediente_nombre": "Mantequilla", "cantidad": 15},
            {"ingrediente_nombre": "Queso de mano", "cantidad": 120},
        ]
    },
    {
        "codigo_receta": "R010",
        "notas_preparacion": "Remoja las arvejas secas en abundante agua desde la noche anterior. Escúrrelas. Coloca las arvejas en una olla con agua limpia y la zanahoria picada en cubos pequeños. Cocina a fuego medio hasta que las arvejas y la zanahoria estén bien blandas. Aparte, prepara un sofrito picando finamente la cebolla, el ají dulce y el ajo machacado. Cocínalos en un sartén pequeño con un toque de agua o aceite y una pizca de comino hasta que estén traslúcidos. Incorpora el sofrito a la olla de las arvejas y mezcla bien. Cocina a fuego lento durante 10 minutos adicionales para que los sabores se integren y el caldo espese. Sazona al gusto y añade el cilantro fresco finamente picado antes de servir.",
        "ingredientes": [
            {"ingrediente_nombre": "Arvejas secas", "cantidad": 250},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 2},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Zanahoria", "cantidad": 1},
            {"ingrediente_nombre": "Comino", "cantidad": 2},
            {"ingrediente_nombre": "Cilantro", "cantidad": 0.25},
        ]
    },
    {
        "codigo_receta": "R011",
        "notas_preparacion": "Remoja los garbanzos secos desde la noche anterior. Cocínalos en agua con una pizca de sal hasta que estén bien tiernos, reservando un poco de su caldo de cocción. En una olla, sofríe a fuego medio la cebolla y el ajo picados en el aceite vegetal junto con el comino. Agrega la espinaca limpia y troceada. Cocina un par de minutos hasta que reduzca su volumen. Incorpora los garbanzos cocidos con un chorrito de su caldo y deja que hierva suavemente para integrar los sabores. Rectifica el punto de sal. Servir caliente acompañado de arroz blanco previamente cocinado.",
        "ingredientes": [
            {"ingrediente_nombre": "Garbanzos secos", "cantidad": 250},
            {"ingrediente_nombre": "Espinaca", "cantidad": 100},
            {"ingrediente_nombre": "Arroz", "cantidad": 150},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 15},
            {"ingrediente_nombre": "Comino", "cantidad": 2},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
        ]
    },
    {
        "codigo_receta": "R014",
        "notas_preparacion": "Pica finamente la cebolla, el tomate, el ají dulce y el ajo machacado. En un sartén caliente, sofríe estos vegetales a fuego medio hasta obtener una salsa integrada, jugosa y suave. Escurre las sardinas en lata, retira con cuidado la espina central si lo prefieres, y añádelas troceadas al sartén con el guiso. Cocina todo junto a fuego bajo durante unos 5 minutos para que las sardinas absorban el sabor del guiso. Apaga el fuego, espolvorea abundante cilantro picado y sirve.",
        "ingredientes": [
            {"ingrediente_nombre": "Sardinas en agua lata", "cantidad": 340},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Tomate", "cantidad": 1},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 1},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Cilantro", "cantidad": 0.25},
        ]
    },
    {
        "codigo_receta": "R016",
        "notas_preparacion": "Pela las papas y córtalas en rodajas finas o dados pequeños. Pica la cebolla finamente. Calienta el aceite vegetal en una sartén y fríe las papas y la cebolla a fuego medio hasta que estén blandas y tiernas (evitando que se tuesten demasiado). Escúrrelas bien del exceso de aceite. En un bol grande, bate los huevos con una pizca de sal. Agrega la mezcla de papas y cebolla escurridas, integrándolo todo bien. En una sartén con apenas un hilo de aceite a fuego medio, vierte la preparación. Deja cocinar hasta que el huevo empiece a cuajar por los bordes y el fondo esté dorado. Con la ayuda de un plato llano grande, dale la vuelta a la tortilla y deslízala de nuevo en la sartén para dorar el otro lado por un par de minutos antes de servir.",
        "ingredientes": [
            {"ingrediente_nombre": "Papa", "cantidad": 350},
            {"ingrediente_nombre": "Huevos", "cantidad": 4},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 20},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
        ]
    },
    {
        "codigo_receta": "R018",
        "notas_preparacion": "Corta las berenjenas en lajas finas. Espolvoréales un toque de sal y déjalas reposar en un colador para que suden y pierdan el amargor. Enjuágalas, sécalas y pásalas por una plancha o sartén caliente hasta que se ablanden ligeramente. Cocina la pasta según las instrucciones del empaque y reserva. Para la bechamel: Derrite la mantequilla en una olla pequeña a fuego bajo, agrega la harina de trigo y remueve por un minuto. Incorpora la leche líquida templada poco a poco sin dejar de batir enérgicamente para evitar grumos, hasta que la salsa espese y cocine bien. En un molde para horno, arma el pasticho alternando capas: una base fina de salsa de tomate, láminas de pasta, lajas de berenjena, salsa bechamel y queso blanco rallado. Repite el orden y finaliza con abundante bechamel y queso blanco por encima. Hornea a 180°C durante 20-25 minutos hasta gratinar.",
        "ingredientes": [
            {"ingrediente_nombre": "Pasta", "cantidad": 200},
            {"ingrediente_nombre": "Berenjena", "cantidad": 1.5},
            {"ingrediente_nombre": "Salsa de tomate", "cantidad": 250},
            {"ingrediente_nombre": "Queso blanco", "cantidad": 120},
            {"ingrediente_nombre": "Leche líquida", "cantidad": 300},
            {"ingrediente_nombre": "Harina de trigo", "cantidad": 25},
            {"ingrediente_nombre": "Mantequilla", "cantidad": 25},
        ]
    },
    {
        "codigo_receta": "R019",
        "notas_preparacion": "Cocina la pasta en abundante agua hirviendo con sal siguiendo el tiempo de cocción indicado en el empaque hasta que esté al dente. Escúrrela. Licúa los tomates maduros (puedes pelarlos previamente si lo deseas) hasta obtener un puré homogéneo. En una olla mediana, sofríe la cebolla y el ajo picados finamente en el aceite vegetal a fuego medio. Añade el tomate licuado, sal al gusto y espolvorea orégano. Cocina la salsa a fuego bajo-medio durante unos 15 a 20 minutos para que espese y concentre sus sabores. Sirve la pasta caliente bañada con la salsa de tomate casera y espolvoreada con el queso blanco rallado.",
        "ingredientes": [
            {"ingrediente_nombre": "Pasta", "cantidad": 250},
            {"ingrediente_nombre": "Tomate", "cantidad": 2.5},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Queso blanco", "cantidad": 60},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 15},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
            {"ingrediente_nombre": "Orégano", "cantidad": 1.5},
        ]
    },
    {
        "codigo_receta": "R021",
        "notas_preparacion": "Filetea la pechuga de pollo en piezas de grosor uniforme. En un recipiente, marina los filetes con el ajo machacado, el jugo de limón, el orégano, el comino, sal y pimienta al gusto. Deja reposar al menos 15 minutos para que absorba los sabores. Calienta muy bien una plancha o sartén antiadherente (puedes pincelarla con un mínimo de grasa si es necesario). Cocina los filetes de pollo a fuego medio-alto durante unos 4-5 minutos por lado, hasta que estén bien dorados por fuera y jugosos y cocidos por dentro. Servir inmediatamente.",
        "ingredientes": [
            {"ingrediente_nombre": "Pechuga de pollo", "cantidad": 350},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Orégano", "cantidad": 2},
            {"ingrediente_nombre": "Comino", "cantidad": 1.5},
            {"ingrediente_nombre": "Limón", "cantidad": 1},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
            {"ingrediente_nombre": "Pimienta", "cantidad": 1},
        ]
    },
    {
        "codigo_receta": "R022",
        "notas_preparacion": "Corta el pollo entero en presas y retira el exceso de grasa. Machaca el ajo. En una olla grande, coloca las piezas de pollo y cúbrelas con agua. Llévala a hervor a fuego medio-alto y retira la espuma que se forme en la superficie. Incorpora a la olla la zanahoria cortada en rodajas, el apio rama picado, el cebollín finamente picado, el ajo machacado y sal al gusto. Baja el fuego a medio, tapa parcialmente la olla y cocina durante unos 35 a 45 minutos hasta que el pollo esté tierno y las verduras cocidas. Sirve el caldo caliente con las presas y vegetales, espolvoreando cilantro fresco picado en cada plato.",
        "ingredientes": [
            {"ingrediente_nombre": "Pollo entero", "cantidad": 600},
            {"ingrediente_nombre": "Zanahoria", "cantidad": 1},
            {"ingrediente_nombre": "Apio rama", "cantidad": 1},
            {"ingrediente_nombre": "Cebollín", "cantidad": 0.5},
            {"ingrediente_nombre": "Cilantro", "cantidad": 0.25},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Sal", "cantidad": 5},
        ]
    },
    {
        "codigo_receta": "R023",
        "notas_preparacion": "Seca bien los filetes de pescado con papel absorbente. Marínalos con el ajo machacado, sal, pimienta y la mitad del jugo de limón. Calienta una plancha o sartén plano a fuego medio-alto y añade el aceite vegetal distribuyéndolo uniformemente por la superficie. Coloca los filetes de pescado con cuidado en la sartén caliente. Cocina durante unos 3 a 4 minutos por lado sin moverlos para evitar que se desarmen, volteando una sola vez cuando el borde se vea opaco. Exprime el resto del jugo de limón por encima de los filetes justo antes de retirarlos de la plancha y sirve caliente.",
        "ingredientes": [
            {"ingrediente_nombre": "Pescado en filetes", "cantidad": 350},
            {"ingrediente_nombre": "Limón", "cantidad": 1},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
            {"ingrediente_nombre": "Pimienta", "cantidad": 1},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 10},
        ]
    },
    {
        "codigo_receta": "R024",
        "notas_preparacion": "Limpia muy bien el pescado de río, córtalo en ruedas o filetes gruesos y lávalo frotándolo suavemente con el jugo de limón. Pica finamente la cebolla, el ají dulce, el tomate y el ajo. En una olla ancha o sartén hondo, sofríe a fuego medio la cebolla, el ajo y el ají dulce hasta que ablanden. Incorpora el tomate picado y cocina unos 5 minutos hasta que suelte sus jugos y forme un guiso base. Coloca las piezas de pescado sobre el colchón de guiso. Si es necesario, añade un cuarto de taza de agua. Tapa la olla y deja cocinar a fuego bajo durante unos 12 a 15 minutos (el vapor del guiso cocinará el pescado). Retira la tapa con cuidado, espolvorea el cilantro fresco finamente picado por encima, rectifica la sazón y sirve caliente con su salsa de cocción.",
        "ingredientes": [
            {"ingrediente_nombre": "Pescado de río", "cantidad": 400},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 1},
            {"ingrediente_nombre": "Tomate", "cantidad": 1},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Cilantro", "cantidad": 0.25},
            {"ingrediente_nombre": "Limón", "cantidad": 0.5},
        ]
    },
    {
        "codigo_receta": "R029",
        "notas_preparacion": "Precalienta el horno a 200°C. Lava muy bien la auyama y córtala en gajos medianos sin retirarle la piel. En un tazón pequeño, mezcla el aceite vegetal con el ajo machacado, el orégano seco, una pizca de sal y pimienta. Coloca los gajos de auyama en una bandeja para hornear y píntalos por ambos lados con la mezcla de aceite sazonado empleando una brocha o con las manos. Hornea durante unos 25 a 30 minutos o hasta que la pulpa esté blanda al pincharla con un tenedor y los bordes se noten ligeramente dorados. Servir como acompañamiento.",
        "ingredientes": [
            {"ingrediente_nombre": "Auyama", "cantidad": 450},
            {"ingrediente_nombre": "Ajo", "cantidad": 2},
            {"ingrediente_nombre": "Orégano", "cantidad": 2},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 15},
            {"ingrediente_nombre": "Sal", "cantidad": 3},
            {"ingrediente_nombre": "Pimienta", "cantidad": 1},
        ]
    },
    {
        "codigo_receta": "R032",
        "notas_preparacion": "Retira la pulpa de los aguacates y colócala en el vaso de la licuadora o procesador de alimentos. Incorpora la cebolla picada en cuartos, el ají dulce (sin venas ni semillas), el cilantro, el perejil y el ajo. Agrega el vinagre, el aceite vegetal y sal al gusto. Licúa o procesa a velocidad media-alta hasta obtener una salsa tersa, cremosa y de color verde brillante. Mantén refrigerada hasta el momento de servir.",
        "ingredientes": [
            {"ingrediente_nombre": "Aguacate", "cantidad": 1.5},
            {"ingrediente_nombre": "Cebolla", "cantidad": 0.5},
            {"ingrediente_nombre": "Ají dulce", "cantidad": 1},
            {"ingrediente_nombre": "Cilantro", "cantidad": 0.25},
            {"ingrediente_nombre": "Perejil", "cantidad": 0.25},
            {"ingrediente_nombre": "Vinagre", "cantidad": 15},
            {"ingrediente_nombre": "Aceite vegetal", "cantidad": 30},
            {"ingrediente_nombre": "Ajo", "cantidad": 1},
            {"ingrediente_nombre": "Sal", "cantidad": 2},
        ]
    },
    {
        "codigo_receta": "R033",
        "notas_preparacion": "En una olla mediana, derrite la mantequilla a fuego medio y sofríe el cebollín picado finamente hasta que esté tierno. Añade las papas cortadas en cubos pequeños y cúbrelas con agua limpia. Cocina a fuego medio-bajo hasta que las papas comiencen a ablandarse. Reduce el fuego al mínimo. Incorpora la leche líquida templada y el queso blanco cortado en cubos pequeños, removiendo suavemente para que todo se caliente y el queso se suavice, sin dejar que la leche llegue a hervir del todo. Casca los huevos uno a uno y agrégalos al caldo con cuidado para que no se rompan las yemas; deja que se cocinen por unos 3 a 5 minutos en el líquido caliente. Apaga el fuego, rectifica la sal, agrega abundante cilantro fresco picado y sirve caliente.",
        "ingredientes": [
            {"ingrediente_nombre": "Papa", "cantidad": 300},
            {"ingrediente_nombre": "Leche líquida", "cantidad": 300},
            {"ingrediente_nombre": "Queso blanco", "cantidad": 100},
            {"ingrediente_nombre": "Huevos", "cantidad": 3},
            {"ingrediente_nombre": "Cebollín", "cantidad": 0.5},
            {"ingrediente_nombre": "Cilantro", "cantidad": 0.25},
            {"ingrediente_nombre": "Mantequilla", "cantidad": 15},
        ]
    },
    {
        "codigo_receta": "R036",
        "nombre": "Arroz con leche",
        "categorias": ["POSTRE"],
        "porciones_base": 6,
        "nivel_costo": "ME",
        "calorias_por_porcion": 180,
        "proteinas_g": Decimal('4.00'),
        "carbohidratos_g": Decimal('32.00'),
        "grasas_g": Decimal('3.00'),
        "fibra_g": Decimal('1.00'),
        "es_vegetariana": True,
        "es_vegana": False,
        "es_sin_gluten": False,
        "es_sin_lactosa": False,
        "notas_preparacion": "En una olla grande, colocar el agua y el arroz. Cocinar a fuego medio hasta que el arroz esté tierno y el agua se haya consumido casi por completo. Añadir la leche líquida y la canela. Reducir el fuego a bajo y cocinar removiendo constantemente para evitar que se pegue. Cuando empiece a espesar, agregar el azúcar y continuar cocinando por unos 10 minutos más. Retirar de la cocción, dejar enfriar a temperatura ambiente y luego refrigerar. Servir frío espolvoreado con canela.",
        "ingredientes": [
            {"ingrediente_nombre": "Arroz", "cantidad": 120},
            {"ingrediente_nombre": "Leche líquida", "cantidad": 600},
            {"ingrediente_nombre": "Azúcar", "cantidad": 90},
            {"ingrediente_nombre": "Canela", "cantidad": 5},
            {"ingrediente_nombre": "Agua", "cantidad": 300},
        ]
    },
    {
        "codigo_receta": "R037",
        "nombre": "Majarete",
        "categorias": ["POSTRE"],
        "porciones_base": 6,
        "nivel_costo": "ME",
        "calorias_por_porcion": 220,
        "proteinas_g": Decimal('3.00'),
        "carbohidratos_g": Decimal('42.00'),
        "grasas_g": Decimal('4.00'),
        "fibra_g": Decimal('2.00'),
        "es_vegetariana": True,
        "es_vegana": False,
        "es_sin_gluten": True,
        "es_sin_lactosa": True,
        "notas_preparacion": "En una olla mediana a fuego medio, disolver el papelón rallado en el agua con la canela para hacer un almíbar ligero. En un tazón aparte, mezclar la harina de maíz precocida con la leche líquida fría y una pizca de sal, removiendo bien para evitar grumos. Colar el almíbar de papelón caliente e incorporarlo lentamente a la mezcla de harina y leche. Llevar la olla a fuego medio-bajo, removiendo constantemente con una cuchara de madera. Cocinar hasta que la mezcla espese y hierva durante unos 8 a 10 minutos. Verter caliente en moldes individuales o en un plato llano. Dejar cuajar y enfriar por completo antes de servir.",
        "ingredientes": [
            {"ingrediente_nombre": "Harina de maíz precocida", "cantidad": 120},
            {"ingrediente_nombre": "Leche líquida", "cantidad": 300},
            {"ingrediente_nombre": "Papelón", "cantidad": 150},
            {"ingrediente_nombre": "Canela", "cantidad": 5},
            {"ingrediente_nombre": "Sal", "cantidad": 1},
            {"ingrediente_nombre": "Agua", "cantidad": 150},
        ]
    },
    {
        "codigo_receta": "R038",
        "nombre": "Galletas de avena",
        "categorias": ["MERIENDA"],
        "porciones_base": 8,
        "nivel_costo": "ME",
        "calorias_por_porcion": 150,
        "proteinas_g": Decimal('3.00'),
        "carbohidratos_g": Decimal('22.00'),
        "grasas_g": Decimal('5.00'),
        "fibra_g": Decimal('2.00'),
        "es_vegetariana": True,
        "es_vegana": False,
        "es_sin_gluten": False,
        "es_sin_lactosa": False,
        "notas_preparacion": "Precalentar el horno a 180°C. En un tazón grande, batir la mantequilla ablandada con el azúcar hasta que quede cremosa. Agregar los huevos uno a uno, mezclando bien. Incorporar la avena en hojuelas y la harina de trigo, revolviendo hasta obtener una masa homogénea. Con una cuchara, tomar porciones de masa y colocarlas espaciadas en una bandeja para hornear engrasada. Hornear durante unos 12 a 15 minutos o hasta que los bordes de las galletas estén dorados. Dejar enfriar en una rejilla antes de consumir.",
        "ingredientes": [
            {"ingrediente_nombre": "Avena en hojuelas", "cantidad": 120},
            {"ingrediente_nombre": "Harina de trigo", "cantidad": 60},
            {"ingrediente_nombre": "Mantequilla", "cantidad": 60},
            {"ingrediente_nombre": "Azúcar", "cantidad": 60},
            {"ingrediente_nombre": "Huevos", "cantidad": 1},
        ]
    },
    {
        "codigo_receta": "R039",
        "nombre": "Plátano horneado con queso",
        "categorias": ["MERIENDA"],
        "porciones_base": 4,
        "nivel_costo": "ME",
        "calorias_por_porcion": 190,
        "proteinas_g": Decimal('5.00'),
        "carbohidratos_g": Decimal('30.00'),
        "grasas_g": Decimal('6.00'),
        "fibra_g": Decimal('3.00'),
        "es_vegetariana": True,
        "es_vegana": False,
        "es_sin_gluten": True,
        "es_sin_lactosa": False,
        "notas_preparacion": "Precalentar el horno a 190°C. Pelar los plátanos maduros. Hacer un corte longitudinal en el centro de cada plátano, sin llegar a cortarlos por completo. Colocarlos en una bandeja para hornear engrasada con un poco de mantequilla. Introducir los plátanos al horno por unos 20 minutos hasta que estén dorados y tiernos. Retirarlos momentáneamente, abrir con cuidado el corte central y rellenar con abundante queso blanco rallado. Volver a meter al horno por 5 a 7 minutos adicionales para que el queso se derrita y dore ligeramente. Servir caliente como merienda dulce y salada.",
        "ingredientes": [
            {"ingrediente_nombre": "Plátano maduro", "cantidad": 2},
            {"ingrediente_nombre": "Queso blanco", "cantidad": 100},
            {"ingrediente_nombre": "Mantequilla", "cantidad": 15},
        ]
    }
]

class Command(BaseCommand):
    help = 'Actualiza las cantidades, notas de preparación y precios de referencia para las 35 recetas e ingredientes del catálogo.'

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
                # 1. Actualización de Precios, Presentación Comercial y Temporada
                self.stdout.write("Actualizando ingredientes (precios, presentación comercial, temporada)...")
                
                # Mapeo de presentaciones comerciales específicas (por defecto: 1000 para gramos/ml, 1 para unidades)
                PRESENTACIONES_COMERCIALES = {
                    "Huevos": Decimal('15.00'),
                    "Comino": Decimal('50.00'),
                    "Pimienta": Decimal('50.00'),
                    "Orégano": Decimal('50.00'),
                    "Canela": Decimal('50.00'),
                }
                
                # Mapeo de temporadas específicas
                TEMPORADAS = {
                    "Aguacate": "VERANO",
                    "Jojoto maíz tierno": "VERANO",
                }

                for nombre_ingrediente, precio in PRECIOS_REFERENCIA.items():
                    try:
                        ingrediente = Ingrediente.objects.get(nombre__iexact=nombre_ingrediente)
                        
                        # Determinar presentación comercial
                        if ingrediente.nombre in PRESENTACIONES_COMERCIALES:
                            ingrediente.presentacion_comercial = PRESENTACIONES_COMERCIALES[ingrediente.nombre]
                        elif ingrediente.unidad_medida in ['gramos', 'ml']:
                            ingrediente.presentacion_comercial = Decimal('1000.00')
                        else:
                            ingrediente.presentacion_comercial = Decimal('1.00')
                        
                        # Determinar temporada
                        if ingrediente.nombre in TEMPORADAS:
                            ingrediente.temporada = TEMPORADAS[ingrediente.nombre]
                        else:
                            ingrediente.temporada = 'TODO'
                        
                        if not dry_run:
                            ingrediente.save(update_fields=['presentacion_comercial', 'temporada'])

                        # Se crea el registro histórico. El signal en models.py actualizará el precio_actual automáticamente.
                        HistorialPrecioIngrediente.objects.create(
                            fk_ingrediente=ingrediente,
                            precio=precio,
                            fecha=timezone.now().date()
                        )
                        self.stdout.write(f" - Ingrediente actualizado: {ingrediente.nombre} (Precio: ${precio}, Pres. Comercial: {ingrediente.presentacion_comercial}, Temporada: {ingrediente.temporada})")
                    except Ingrediente.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f" [!] Ingrediente '{nombre_ingrediente}' no encontrado al actualizar."))

                # 2. Procesamiento de Recetas
                self.stdout.write("Procesando recetas curadas...")
                for datos in CANTIDADES_RECETAS:
                    codigo = datos["codigo_receta"]
                    try:
                        receta = Receta.objects.get(codigo=codigo)
                    except Receta.DoesNotExist:
                        # Si no existe y tiene metadatos en datos (ej: R036-R039), la creamos sobre la marcha
                        if "nombre" in datos:
                            self.stdout.write(f"Creando receta faltante {codigo} - {datos['nombre']}...")
                            receta = Receta.objects.create(
                                codigo=codigo,
                                nombre=datos["nombre"],
                                porciones_base=datos["porciones_base"],
                                calorias_por_porcion=datos["calorias_por_porcion"],
                                proteinas_g=datos["proteinas_g"],
                                carbohidratos_g=datos["carbohidratos_g"],
                                grasas_g=datos["grasas_g"],
                                fibra_g=datos["fibra_g"],
                                nivel_costo=datos["nivel_costo"],
                                es_vegetariana=datos["es_vegetariana"],
                                es_vegana=datos["es_vegana"],
                                es_sin_gluten=datos["es_sin_gluten"],
                                es_sin_lactosa=datos["es_sin_lactosa"],
                                notas_preparacion=datos["notas_preparacion"]
                            )
                            # Vincular categorías
                            for cat_slug in datos["categorias"]:
                                try:
                                    cat = Categoria.objects.get(slug=cat_slug.lower())
                                    from catalogo.models import RecetaCategoria
                                    RecetaCategoria.objects.get_or_create(fk_receta=receta, fk_categoria=cat)
                                except Categoria.DoesNotExist:
                                    pass
                        else:
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
                            
                        # Usar update_or_create para asegurar idempotencia sin duplicar
                        if not dry_run:
                            ri, created = RecetaIngrediente.objects.update_or_create(
                                fk_receta=receta,
                                fk_ingrediente=ingrediente,
                                defaults={'cantidad': cantidad}
                            )
                        else:
                            try:
                                ri = RecetaIngrediente.objects.get(fk_receta=receta, fk_ingrediente=ingrediente)
                                created = False
                            except RecetaIngrediente.DoesNotExist:
                                created = True
                                
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
