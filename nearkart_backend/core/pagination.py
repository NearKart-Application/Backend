"""
NearKart — Pagination Classes
"""
from rest_framework.pagination import CursorPagination, PageNumberPagination


class StandardCursorPagination(CursorPagination):
    """
    Cursor-based pagination for infinite scroll feeds.
    Used for: video feed, product feed, message list.
    Stable ordering — safe for real-time data.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50
    ordering = '-created_at'
    cursor_query_param = 'cursor'


class StandardOffsetPagination(PageNumberPagination):
    """
    Offset-based pagination for manageable lists.
    Used for: store list, analytics, invoice list.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'
