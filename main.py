from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import os


# Carga .env solo en desarrollo (local)
if os.getenv("RAILWAY_ENVIRONMENT") is None:  # Si no está en Railway
    from dotenv import load_dotenv
    load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
)



SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


supabase : Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class Category(BaseModel):
    nombre: str

class ProductCategory(BaseModel):
    category: Category

class Product(BaseModel):
    id: Optional[int] = None
    name: str = Field(alias="nombre")
    description: Optional[str] = Field(None, alias="descripcion")
    image: Optional[str] = Field(None, alias="imagen")
    price: float = Field(alias="precio", ge=0)
    rating: Optional[float] = Field(None, alias="rating", ge=1, le=5)
    category_product: List[ProductCategory] = []

class UserLogin(BaseModel):
    nombre_usuario: str
    contraseña: str

class CartItem(BaseModel):
    id_user: int
    id_product: int
    quantity: int = Field(ge=1)

class CartItemList(BaseModel):
    items: List[CartItem]

class Purchase(BaseModel):
    id_user: int
    id_product: int
    quantity: int
    total_price: float

@app.post("/login")
def login_user(user: UserLogin):
    try:
        response = supabase.table("user").select("*").eq("nombre_usuario", user.nombre_usuario).eq("contraseña", user.contraseña).execute()
        if not response.data:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
        return {"status": "ok", "msg": "Login exitoso", "user": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al hacer login: {str(e)}")


@app.post("/addProduct")
def create_product(prod: Product):
    try:
        existing_product = supabase.table("product").select("*").eq("nombre", prod.nombre).execute()
        if existing_product.data:
            raise HTTPException(status_code=400, detail="El producto ya existe")
        response = supabase.table("product").insert(prod.model_dump()).execute()
        return {"status": "ok", "msg": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear el producto: {str(e)}")

@app.get("/products", response_model=List[Product])
def list_products():
    response = supabase.table("product").select("""
        *,
        category_product (
            category (
                nombre
            )
        )
    """).execute()
    
    if response.data:
        return response.data
    else:
        raise HTTPException(status_code=404, detail="No se encontraron registros")

@app.get("/categories", response_model=List[Category])
def list_categories():
    response = supabase.table("category").select("*").execute()
    if response.data:
        return response.data
    else:
        raise HTTPException(status_code=404, detail="No se encontraron categorías")

@app.post("/cart")
def add_to_cart(cart: CartItemList):
    try:
        # Validar que la lista de ítems no esté vacía
        if not cart.items:
            raise HTTPException(status_code=400, detail="La lista de ítems no puede estar vacía")

        inserted_items = []
        for item in cart.items:
            # Validar que la cantidad sea positiva
            if item.quantity <= 0:
                raise HTTPException(status_code=400, detail=f"La cantidad del producto {item.id_product} debe ser mayor que 0")

            # Insertar un registro por cada unidad del producto
            for _ in range(item.quantity):
                response = supabase.table("purchases_Made").insert({
                    "id_user": item.id_user,
                    "id_product": item.id_product,
                }).execute()
                inserted_items.extend(response.data)

        return {
            "status": "ok",
            "msg": f"{sum(item.quantity for item in cart.items)} unidad(es) de producto(s) comprada(s) extitosamente",
            "data": inserted_items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al agregar al carrito: {str(e)}")

@app.get("/purchases/{user_id}")
def get_user_purchases(user_id: int):
    try:
        response = supabase.table("purchases_Made").select("""
            *,
            product (
                nombre,
                precio,
                imagen
            )
        """).eq("id_user", user_id).execute()
        
        if response.data:
            return {"purchases": response.data}
        else:
            return {"purchases": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener compras: {str(e)}")