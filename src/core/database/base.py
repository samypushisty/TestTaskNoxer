from datetime import datetime
from typing import Annotated, Optional, List, Any, Dict
from sqlalchemy import ForeignKey, Text, MetaData, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sqlalchemy.orm import DeclarativeBase
from core.config import settings
from core.database.db_helper import db_helper


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention=settings.db.naming_convention
    )

    def to_dict(self):
        """Базовый метод для преобразования объекта в словарь"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


intpk = Annotated[int, mapped_column(primary_key=True)]
intpkfk = Annotated[int, mapped_column(ForeignKey('products.product_id', ondelete="CASCADE"), primary_key=True)]


# Ассоциативные таблицы (без изменений)
class ProductCategoryAssociation(Base):
    __tablename__ = 'product_category_association'
    product_id: Mapped[int] = mapped_column(ForeignKey('products.product_id', ondelete="CASCADE"), primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.category_id', ondelete="CASCADE"), primary_key=True)


class ProductMarkAssociation(Base):
    __tablename__ = 'product_mark_association'
    product_id: Mapped[int] = mapped_column(ForeignKey('products.product_id', ondelete="CASCADE"), primary_key=True)
    mark_id: Mapped[int] = mapped_column(ForeignKey('product_marks.mark_id', ondelete="CASCADE"), primary_key=True)


# Основные модели с методами to_dict()
class Category(Base):
    __tablename__ = "categories"

    category_id: Mapped[intpk]
    category_image: Mapped[str]
    category_name: Mapped[str]
    sort_order: Mapped[Optional[int]]

    products: Mapped[List["Product"]] = relationship(
        secondary="product_category_association",
        back_populates="categories",
        cascade="all, delete",
        lazy="selectin"
    )

    def to_dict(self):
        """Преобразует объект категории в словарь"""
        return {
            "category_id": self.category_id,
            "category_name": self.category_name,
            "category_image": self.category_image,
            "sort_order": self.sort_order
        }


class ProductMark(Base):
    __tablename__ = "product_marks"

    mark_id: Mapped[intpk]
    mark_name: Mapped[str]

    products: Mapped[List["Product"]] = relationship(
        secondary="product_mark_association",
        back_populates="marks",
        cascade="all, delete",
        lazy="selectin"
    )

    def to_dict(self):
        """Преобразует объект метки продукта в словарь"""
        return {
            "mark_id": self.mark_id,
            "mark_name": self.mark_name
        }


class Product(Base):
    __tablename__ = "products"

    created_at: Mapped[datetime]
    on_main: Mapped[bool]
    product_id: Mapped[intpk]
    product_name: Mapped[str]
    updated_at: Mapped[datetime]
    moysklad_connector_products_data: Mapped[Optional[str]]
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON)

    # Отношения
    categories: Mapped[List["Category"]] = relationship(secondary="product_category_association", cascade="all, delete",
                                                        lazy="selectin")
    colors: Mapped[List["ProductColor"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    excluded: Mapped[List["ExcludedCombination"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    extras: Mapped[List["ProductExtra"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    images: Mapped[List["ProductImage"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    importance_items: Mapped[List["ImportanceItem"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    marks: Mapped[List["ProductMark"]] = relationship(secondary="product_mark_association", cascade="all, delete",
                                                      lazy="selectin")
    parameters: Mapped[List["ProductParameter"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    reviews: Mapped[List["ProductReview"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    videos: Mapped[List["ProductVideo"]] = relationship(cascade="all, delete-orphan", lazy="selectin")

    def to_dict(self, include_relations=True):
        """
        Преобразует объект продукта в словарь

        Args:
            include_relations: Включать ли связанные объекты (по умолчанию True)
        """
        product_dict = {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "on_main": self.on_main,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "moysklad_connector_products_data": self.moysklad_connector_products_data,
            "tags": self.tags
        }

        if include_relations:
            product_dict.update({
                "categories": [category.to_dict() for category in self.categories],
                "colors": [color.to_dict() for color in self.colors],
                "marks": [mark.to_dict() for mark in self.marks],
                "parameters": [parameter.to_dict() for parameter in self.parameters],
                "images": [image.to_dict() for image in self.images],
                "extras": [extra.to_dict() for extra in self.extras],
                "reviews": [review.to_dict() for review in self.reviews],
                "videos": [video.to_dict() for video in self.videos]
            })

        return product_dict


class ProductColor(Base):
    __tablename__ = "product_colors"

    color_code: Mapped[str]
    color_id: Mapped[intpk]
    color_name: Mapped[str]
    color_image: Mapped[Optional[str]]
    product_id: Mapped[intpkfk]
    discount: Mapped[Optional[float]]
    json_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    sort_order: Mapped[Optional[int]]

    def to_dict(self):
        """Преобразует объект цвета продукта в словарь"""
        return {
            "color_id": self.color_id,
            "color_name": self.color_name,
            "color_code": self.color_code,
            "color_image": self.color_image,
            "discount": self.discount,
            "json_data": self.json_data,
            "sort_order": self.sort_order
        }


class ProductImage(Base):
    __tablename__ = "product_images"

    image_id: Mapped[intpk]
    image_url: Mapped[str]
    main_image: Mapped[bool]
    product_id: Mapped[intpkfk]
    position: Mapped[Optional[str]]
    sort_order: Mapped[Optional[int]]
    title: Mapped[Optional[str]]

    def to_dict(self):
        """Преобразует объект изображения продукта в словарь"""
        return {
            "image_id": self.image_id,
            "image_url": self.image_url,
            "main_image": self.main_image,
            "position": self.position,
            "sort_order": self.sort_order,
            "title": self.title
        }


class ProductParameter(Base):
    __tablename__ = "product_parameters"

    parameter_id: Mapped[intpk]
    chosen: Mapped[bool]
    disabled: Mapped[bool]
    extra_field_color: Mapped[Optional[str]]
    extra_field_image: Mapped[Optional[str]]
    name: Mapped[str]
    old_price: Mapped[Optional[float]]
    parameter_string: Mapped[str]
    price: Mapped[float]
    sort_order: Mapped[Optional[int]]
    product_id: Mapped[intpkfk]

    def to_dict(self):
        """Преобразует объект параметра продукта в словарь"""
        return {
            "parameter_id": self.parameter_id,
            "name": self.name,
            "parameter_string": self.parameter_string,
            "price": self.price,
            "old_price": self.old_price,
            "chosen": self.chosen,
            "disabled": self.disabled,
            "extra_field_color": self.extra_field_color,
            "extra_field_image": self.extra_field_image,
            "sort_order": self.sort_order
        }


class ProductExtra(Base):
    __tablename__ = "product_extras"

    characteristics: Mapped[Optional[str]] = mapped_column(Text)
    delivery: Mapped[Optional[str]] = mapped_column(Text)
    kit: Mapped[Optional[str]] = mapped_column(Text)
    offer: Mapped[Optional[str]] = mapped_column(Text)
    product_extra_id: Mapped[intpk]
    product_id: Mapped[intpkfk]
    ai_description: Mapped[Optional[str]] = mapped_column(Text)

    def to_dict(self):
        """Преобразует объект дополнительной информации продукта в словарь"""
        return {
            "product_extra_id": self.product_extra_id,
            "characteristics": self.characteristics,
            "delivery": self.delivery,
            "kit": self.kit,
            "offer": self.offer,
            "ai_description": self.ai_description
        }


class ProductReview(Base):
    __tablename__ = "product_reviews"
    photo_id: Mapped[intpk]
    photo_url: Mapped[str]
    product_id: Mapped[intpkfk]
    sort_order: Mapped[Optional[int]]

    def to_dict(self):
        """Преобразует объект отзыва продукта в словарь"""
        return {
            "photo_id": self.photo_id,
            "photo_url": self.photo_url,
            "sort_order": self.sort_order
        }


class ProductVideo(Base):
    __tablename__ = "product_videos"

    poster_url: Mapped[Optional[str]]
    product_id: Mapped[intpkfk]
    video_id: Mapped[intpk]
    video_url: Mapped[str]
    sort_order: Mapped[Optional[int]]

    def to_dict(self):
        """Преобразует объект видео продукта в словарь"""
        return {
            "video_id": self.video_id,
            "video_url": self.video_url,
            "poster_url": self.poster_url,
            "sort_order": self.sort_order
        }


class ExcludedCombination(Base):
    __tablename__ = "excluded_combinations"

    id: Mapped[intpk]
    color_id: Mapped[int]
    parameter_id: Mapped[int]
    product_id: Mapped[intpkfk]

    def to_dict(self):
        """Преобразует объект исключенной комбинации в словарь"""
        return {
            "id": self.id,
            "color_id": self.color_id,
            "parameter_id": self.parameter_id
        }


class ImportanceItem(Base):
    __tablename__ = "importance_items"

    id: Mapped[intpk]
    importance: Mapped[int]
    product_id: Mapped[intpkfk]

    def to_dict(self):
        """Преобразует объект важного элемента в словарь"""
        return {
            "id": self.id,
            "importance": self.importance
        }

class ProjectParameter(Base):
    """Хранение параметров из special_project_parameters"""
    __tablename__ = 'project_parameters'

    id: Mapped[intpk]
    description: Mapped[Optional[str]]  # Описание параметра
    value: Mapped[str]  # Основное значение


class ProjectAction(Base):
    """Хранение действий из special_project_parameters_actions"""
    __tablename__ = 'project_actions'

    id: Mapped[intpk]
    action_type: Mapped[str]  # Тип действия
    description: Mapped[str]  # Описание действия
    image_url: Mapped[Optional[str]]  # URL изображения
    url: Mapped[Optional[str]]  # Ссылка для действия
    sort_order: Mapped[int]  # Порядок сортировки
    extra_field_1: Mapped[Optional[str]]  # Доп поле 1
    extra_field_2: Mapped[Optional[str]]  # Доп поле 2


class ProjectBadge(Base):
    """Хранение бейджей из special_project_parameters_badges"""
    __tablename__ = 'project_badges'

    id: Mapped[intpk]
    description: Mapped[str]  # Описание бейджа
    image_url: Mapped[str]  # URL изображения
    meaning_tag: Mapped[Optional[str]]  # Тег значения
    url: Mapped[Optional[str]]  # Ссылка
    sort_order: Mapped[int]  # Порядок сортировки


class ProjectJsonConfig(Base):
    """Хранение конфигов из special_project_parameters_json"""
    __tablename__ = 'project_json_configs'

    id: Mapped[intpk]
    config_type: Mapped[Optional[str]] = mapped_column(unique=True)
    config_data: Mapped[Dict[str, Any]] = mapped_column(JSON)

if __name__ == "__main__":
    Base.metadata.create_all(db_helper.engine)