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
    category_product: List[ProductCategory] = [] # Changed to List to match the Supabase schema


# Endpoints
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