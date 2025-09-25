"""
Script to populate default resource categories and migrate existing data
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update
from app.core.config import settings
from app.models.knowledge import ResourceCategory, UsefulLink, DownloadableDocument

# Default categories with metadata
DEFAULT_CATEGORIES = [
    {
        "name": "RH",
        "description": "Recursos Humanos - Férias, folha de pagamento, benefícios",
        "icon": "users",
        "color_code": "#4A90E2",
        "order": 1
    },
    {
        "name": "TI",
        "description": "Tecnologia da Informação - Sistemas, suporte técnico, acessos",
        "icon": "computer",
        "color_code": "#7B68EE",
        "order": 2
    },
    {
        "name": "Financeiro",
        "description": "Departamento Financeiro - Reembolsos, notas fiscais, pagamentos",
        "icon": "dollar-sign",
        "color_code": "#2ECC71",
        "order": 3
    },
    {
        "name": "Compliance",
        "description": "Conformidade - Políticas, regulamentos, código de ética",
        "icon": "shield",
        "color_code": "#E74C3C",
        "order": 4
    },
    {
        "name": "Vendas",
        "description": "Departamento Comercial - CRM, propostas, contratos",
        "icon": "trending-up",
        "color_code": "#F39C12",
        "order": 5
    },
    {
        "name": "Marketing",
        "description": "Marketing - Campanhas, materiais, marca",
        "icon": "megaphone",
        "color_code": "#9B59B6",
        "order": 6
    },
    {
        "name": "Operações",
        "description": "Operações - Processos, logística, qualidade",
        "icon": "settings",
        "color_code": "#34495E",
        "order": 7
    },
    {
        "name": "Geral",
        "description": "Recursos gerais e diversos",
        "icon": "folder",
        "color_code": "#95A5A6",
        "order": 99
    }
]

async def populate_categories(session: AsyncSession):
    """Create default categories if they don't exist"""
    created_categories = {}

    for cat_data in DEFAULT_CATEGORIES:
        # Check if category exists
        result = await session.execute(
            select(ResourceCategory).where(ResourceCategory.name == cat_data["name"])
        )
        category = result.scalar_one_or_none()

        if not category:
            # Create new category
            category = ResourceCategory(
                name=cat_data["name"],
                description=cat_data["description"],
                icon=cat_data["icon"],
                color_code=cat_data["color_code"],
                order=cat_data["order"],
                is_active=True
            )
            session.add(category)
            await session.flush()  # Get the ID
            print(f"✅ Created category: {cat_data['name']}")
        else:
            print(f"ℹ️ Category already exists: {cat_data['name']}")

        created_categories[cat_data["name"]] = category.id

    await session.commit()
    return created_categories

async def migrate_existing_data(session: AsyncSession, categories_map: dict):
    """Migrate existing links and documents to use category_id"""

    # Migrate useful_links
    result = await session.execute(
        select(UsefulLink).where(UsefulLink.category_id == None)
    )
    links = result.scalars().all()

    for link in links:
        if link.category and link.category in categories_map:
            link.category_id = categories_map[link.category]
            print(f"✅ Migrated link '{link.title}' to category_id {link.category_id}")
        elif link.category:
            # Create category if doesn't exist
            result = await session.execute(
                select(ResourceCategory).where(ResourceCategory.name == link.category)
            )
            category = result.scalar_one_or_none()

            if not category:
                category = ResourceCategory(
                    name=link.category,
                    description=f"Auto-created category for {link.category}",
                    is_active=True,
                    order=100
                )
                session.add(category)
                await session.flush()
                print(f"✅ Created new category: {link.category}")

            link.category_id = category.id
            categories_map[link.category] = category.id

    # Migrate downloadable_documents
    result = await session.execute(
        select(DownloadableDocument).where(DownloadableDocument.category_id == None)
    )
    documents = result.scalars().all()

    for doc in documents:
        if doc.category and doc.category in categories_map:
            doc.category_id = categories_map[doc.category]
            print(f"✅ Migrated document '{doc.title}' to category_id {doc.category_id}")
        elif doc.category:
            # Create category if doesn't exist
            result = await session.execute(
                select(ResourceCategory).where(ResourceCategory.name == doc.category)
            )
            category = result.scalar_one_or_none()

            if not category:
                category = ResourceCategory(
                    name=doc.category,
                    description=f"Auto-created category for {doc.category}",
                    is_active=True,
                    order=100
                )
                session.add(category)
                await session.flush()
                print(f"✅ Created new category: {doc.category}")

            doc.category_id = category.id
            categories_map[doc.category] = category.id

    await session.commit()
    print(f"\n✅ Migration completed!")
    print(f"   - Migrated {len(links)} links")
    print(f"   - Migrated {len(documents)} documents")

async def main():
    """Main migration function"""
    print("🚀 Starting category migration...")

    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Step 1: Populate default categories
        print("\n📁 Creating default categories...")
        categories_map = await populate_categories(session)

        # Step 2: Migrate existing data
        print("\n🔄 Migrating existing data...")
        await migrate_existing_data(session, categories_map)

    await engine.dispose()
    print("\n✅ All done!")

if __name__ == "__main__":
    asyncio.run(main())