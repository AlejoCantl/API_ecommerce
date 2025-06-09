from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from supabase import create_client
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import os

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL y SUPABASE_KEY deben estar definidas en el archivo .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Models
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

class UserRegister(BaseModel):
    nombre: str
    apellido: str
    nombre_usuario: str
    contraseña: str

class UserLogin(BaseModel):
    nombre_usuario: str
    contraseña: str

# Nuevos endpoints
@app.post("/register")
def register_user(user: UserRegister):
    try:
        existing_user = supabase.table("user").select("*").eq("nombre_usuario", user.nombre_usuario).execute()
        if existing_user.data:
            raise HTTPException(status_code=400, detail="El usuario ya existe")
        
        supabase.table("user").insert(user.model_dump()).execute()
        return {"status": "ok", "msg": "Usuario registrado exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al registrar usuario: {str(e)}")

@app.post("/login")
def login_user(user: UserLogin):
    try:
        response = supabase.table("user").select("*").eq("nombre_usuario", user.nombre_usuario).eq("contraseña", user.contraseña).execute()
        if not response.data:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
        return {"status": "ok", "msg": "Login exitoso", "user": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al hacer login: {str(e)}")

@app.get("/products/search")
def search_products(
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None
):
    try:
        query = supabase.table("product").select("""
            *,
            category_product (
                category (
                    nombre
                )
            )
        """)
        
        if category_id:
            category_products = supabase.table("category_product").select("id_product").eq("id_category", category_id).execute()
            if category_products.data:
                product_ids = [cp["id_product"] for cp in category_products.data]
                query = query.in_("id", product_ids)
        
        if min_price is not None:
            query = query.gte("precio", min_price)
        
        if max_price is not None:
            query = query.lte("precio", max_price)
        
        if search:
            query = query.ilike("nombre", f"%{search}%")
        
        response = query.execute()
        return {"products": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar productos: {str(e)}")

# Endpoints existentes
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