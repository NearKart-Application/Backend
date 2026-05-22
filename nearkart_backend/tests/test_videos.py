"""
Tests — Video Module
Covers: request upload, confirm upload, feed, detail, like/unlike, delete, download
"""
import pytest
from apps.videos.models import Video


BASE = '/api/v1/videos'


@pytest.fixture
def video(db, store):
    from django.utils import timezone
    from datetime import timedelta
    return Video.objects.create(
        store=store,
        title='Summer Sale',
        description='Big discounts',
        raw_s3_key='videos/raw/store/test-id/original.mp4',
        hls_s3_key='videos/hls/store/test-id/master.m3u8',
        video_url='https://mock-s3.dev/videos/hls/test-id/master.m3u8?dev=true',
        thumbnail_url='https://mock-s3.dev/videos/thumbnails/test-id/thumb.jpg?dev=true',
        status=Video.STATUS_READY,
        is_visible=True,
        location=store.location,
        expires_at=timezone.now() + timedelta(days=25),
    )


@pytest.fixture
def expired_video(db, store):
    from django.utils import timezone
    from datetime import timedelta
    return Video.objects.create(
        store=store,
        title='Old Video',
        status=Video.STATUS_EXPIRED,
        is_visible=False,
        location=store.location,
        expires_at=timezone.now() - timedelta(days=1),
    )


# ── Request Upload ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_request_upload(vendor_client, store):
    response = vendor_client.post(f'{BASE}/request-upload/', {
        'title': 'New Video',
        'description': 'Test upload',
    })
    assert response.status_code == 201
    data = response.json()
    assert 'video_id' in data
    assert 'upload_url' in data
    assert Video.objects.filter(store=store, title='New Video').exists()


@pytest.mark.django_db
def test_request_upload_customer_forbidden(customer_client):
    response = customer_client.post(f'{BASE}/request-upload/', {'title': 'Nope'})
    assert response.status_code == 403


@pytest.mark.django_db
def test_request_upload_no_store(vendor_client, vendor_user):
    response = vendor_client.post(f'{BASE}/request-upload/', {'title': 'No Store'})
    assert response.status_code in (400, 404)


# ── Confirm Upload ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_confirm_upload(vendor_client, store):
    req = vendor_client.post(f'{BASE}/request-upload/', {'title': 'Confirm Me'})
    video_id = req.json()['video_id']

    response = vendor_client.post(f'{BASE}/{video_id}/confirm-upload/', {
        'duration_seconds': 45,
    })
    assert response.status_code == 200
    video = Video.objects.get(id=video_id)
    assert video.status == Video.STATUS_READY  # dev mode skips transcoding


@pytest.mark.django_db
def test_confirm_upload_exceeds_max_duration(vendor_client, store):
    req = vendor_client.post(f'{BASE}/request-upload/', {'title': 'Too Long'})
    video_id = req.json()['video_id']
    response = vendor_client.post(f'{BASE}/{video_id}/confirm-upload/', {
        'duration_seconds': 999,
    })
    assert response.status_code == 400


@pytest.mark.django_db
def test_confirm_upload_other_vendor_forbidden(vendor2_client, store):
    from rest_framework.test import APIClient
    from tests.conftest import make_token
    req_client = APIClient()
    req_client.credentials(HTTP_AUTHORIZATION=f'Bearer {make_token(store.owner)}')
    req = req_client.post(f'{BASE}/request-upload/', {'title': 'Yours'})
    video_id = req.json()['video_id']
    response = vendor2_client.post(f'{BASE}/{video_id}/confirm-upload/', {'duration_seconds': 30})
    assert response.status_code in (403, 404)


# ── My Videos ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_my_videos(vendor_client, video):
    response = vendor_client.get(f'{BASE}/my-videos/')
    assert response.status_code == 200
    results = response.json().get('results', response.json())
    titles = [v['title'] for v in (results if isinstance(results, list) else [])]
    assert 'Summer Sale' in titles


@pytest.mark.django_db
def test_my_videos_customer_forbidden(customer_client):
    response = customer_client.get(f'{BASE}/my-videos/')
    assert response.status_code == 403


# ── Feed ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_video_feed_returns_results(customer_client, video):
    response = customer_client.get(f'{BASE}/feed/?lat=13.0827&lng=80.2707')
    assert response.status_code == 200


@pytest.mark.django_db
def test_video_feed_excludes_expired(customer_client, expired_video):
    response = customer_client.get(f'{BASE}/feed/?lat=13.0827&lng=80.2707')
    assert response.status_code == 200
    results = response.json().get('results', response.json())
    titles = [v['title'] for v in (results if isinstance(results, list) else [])]
    assert 'Old Video' not in titles


@pytest.mark.django_db
def test_video_feed_missing_coords(customer_client):
    response = customer_client.get(f'{BASE}/feed/')
    assert response.status_code == 400


# ── Video Detail ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_video_detail(anon_client, video):
    response = anon_client.get(f'{BASE}/{video.id}/')
    assert response.status_code == 200
    assert response.json()['title'] == 'Summer Sale'


@pytest.mark.django_db
def test_video_detail_increments_view_count(anon_client, video):
    view_before = video.view_count
    anon_client.get(f'{BASE}/{video.id}/')
    video.refresh_from_db()
    assert video.view_count == view_before + 1


@pytest.mark.django_db
def test_video_detail_not_found(anon_client):
    response = anon_client.get(f'{BASE}/00000000-0000-0000-0000-000000000000/')
    assert response.status_code == 404


# ── Like / Unlike ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_like_video(customer_client, video):
    response = customer_client.post(f'{BASE}/{video.id}/like/')
    assert response.status_code == 200
    assert response.json()['liked'] is True


@pytest.mark.django_db
def test_unlike_video(customer_client, customer, video):
    from apps.videos.models import VideoLike
    VideoLike.objects.create(user=customer, video=video)
    response = customer_client.post(f'{BASE}/{video.id}/like/')
    assert response.status_code == 200
    assert response.json()['liked'] is False


@pytest.mark.django_db
def test_like_requires_auth(anon_client, video):
    response = anon_client.post(f'{BASE}/{video.id}/like/')
    assert response.status_code == 401


# ── Delete ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_delete_video_owner(vendor_client, video):
    response = vendor_client.delete(f'{BASE}/{video.id}/delete/')
    assert response.status_code == 204
    assert not Video.objects.filter(id=video.id).exists()


@pytest.mark.django_db
def test_delete_video_other_vendor(vendor2_client, video):
    response = vendor2_client.delete(f'{BASE}/{video.id}/delete/')
    assert response.status_code in (403, 404)
    assert Video.objects.filter(id=video.id).exists()


# ── Download ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_download_video_owner(vendor_client, video):
    response = vendor_client.get(f'{BASE}/{video.id}/download/')
    assert response.status_code == 200
    data = response.json()
    assert 'download_url' in data
    assert data['expires_in'] == 3600
    assert 'download' in data['download_url']


@pytest.mark.django_db
def test_download_video_other_vendor(vendor2_client, video):
    response = vendor2_client.get(f'{BASE}/{video.id}/download/')
    assert response.status_code == 404


@pytest.mark.django_db
def test_download_video_customer_forbidden(customer_client, video):
    response = customer_client.get(f'{BASE}/{video.id}/download/')
    assert response.status_code == 403


@pytest.mark.django_db
def test_download_video_no_raw_key(vendor_client, store):
    video = Video.objects.create(
        store=store, title='No Raw', status=Video.STATUS_READY,
        raw_s3_key='', is_visible=True, location=store.location,
    )
    response = vendor_client.get(f'{BASE}/{video.id}/download/')
    assert response.status_code == 409
