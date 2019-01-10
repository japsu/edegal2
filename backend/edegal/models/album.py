import logging

from django.conf import settings
from django.db import models
from django.shortcuts import get_object_or_404

from ..utils import slugify, pick_attrs
from .common import CommonFields


logger = logging.getLogger(__name__)


class Album(models.Model):
    slug = models.CharField(**CommonFields.slug)
    parent = models.ForeignKey('self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='subalbums',
        db_index=True,
        verbose_name='Parent Album',
        help_text='The album under which this album will reside. The root album (/) has no parent album.'
    )
    path = models.CharField(**CommonFields.path)

    title = models.CharField(**CommonFields.title)
    description = models.TextField(**CommonFields.description)

    body = models.TextField(
        blank=True,
        default='',
        verbose_name='Text content',
        help_text='Will be displayed at the top of the album view before subalbums and pictures.',
    )

    redirect_url = models.CharField(
        max_length=1023,
        blank=True,
        verbose_name='Redirect URL',
        help_text='If set, users that stumble upon this album will be redirected to this URL.',
    )

    cover_picture = models.ForeignKey('Picture',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    is_public = models.BooleanField(**CommonFields.is_public)
    is_visible = models.BooleanField(**CommonFields.is_visible)

    terms_and_conditions = models.ForeignKey('edegal.TermsAndConditions',
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(null=True, auto_now_add=True)
    updated_at = models.DateTimeField(null=True, auto_now=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True)

    def __init__(self, *args, **kwargs):
        super(Album, self).__init__(*args, **kwargs)
        self.__original_path = self.path

    def as_dict(self, include_hidden=False, format='jpeg'):
        child_criteria = dict()
        if not include_hidden:
            child_criteria.update(is_public=True)

        return pick_attrs(self,
            'slug',
            'path',
            'title',
            'description',
            'body',
            'redirect_url',

            breadcrumb=[ancestor._make_breadcrumb() for ancestor in self.get_ancestors()],
            subalbums=[
                subalbum._make_subalbum(format=format)
                for subalbum in self.subalbums.filter(is_visible=True, **child_criteria).select_related('cover_picture')
            ],
            pictures=[
                picture.as_dict(format=format)
                for picture in self.pictures.filter(**child_criteria).prefetch_related('media')
            ],
            terms_and_conditions=(
                self.terms_and_conditions.as_dict()
                if self.terms_and_conditions
                else None
            ),
        )

    def _make_thumbnail(self, format):
        # TODO what if the thumbnail is hidden?
        if self.cover_picture:
            return self.cover_picture.get_media('thumbnail', format=format).as_dict()
        else:
            return None

    def _make_breadcrumb(self):
        return pick_attrs(self,
            'path',
            'title',
        )

    def _make_subalbum(self, format):
        return pick_attrs(self,
            'path',
            'title',
            thumbnail=self._make_thumbnail(format=format),
        )

    def _make_path(self):
        if self.parent is None:
            return '/'
        else:
            # XX ugly
            pth = self.parent.path + '/' + self.slug
            if pth.startswith('//'):
                pth = pth[1:]
            return pth

    def _select_cover_picture(self):
        first_subalbum = self.subalbums.filter(cover_picture__isnull=False).first()
        if first_subalbum is not None:
            return first_subalbum.cover_picture

        first_picture = self.pictures.first()
        if first_picture is not None:
            return first_picture

        return None

    def save(self, *args, **kwargs):
        traverse = kwargs.pop('traverse', True)

        if self.title and not self.slug:
            if self.parent:
                self.slug = slugify(self.title)
            else:
                self.slug = '-root-album'

        path_changed = False
        if self.slug:
            self.path = self._make_path()
            path_changed = self.path != self.__original_path

        if self.cover_picture is None:
            self.cover_picture = self._select_cover_picture()

        return_value = super(Album, self).save(*args, **kwargs)

        # In case path changed, update child pictures' paths.
        for picture in self.pictures.all():
            picture.save()

        # In case thumbnails or path changed, update whole family with updated information.
        if traverse:
            if path_changed:
                family = self.get_family(include_self=False)
            else:
                family = self.get_ancestors(include_self=False)

            for album in family:
                logger.debug('Album.save(traverse=True) visiting {path}'.format(path=album.path))
                album.save(traverse=False)

        return return_value

    @classmethod
    def get_album_by_path(cls, path, or_404=False, **extra_criteria):
        # Is it a picture?
        from .picture import Picture
        try:
            picture = Picture.objects.only('album_id').get(path=path)
        except Picture.DoesNotExist:
            query = dict(path=path, **extra_criteria)
        else:
            query = dict(id=picture.album_id, **extra_criteria)

        queryset = (
            cls.objects.filter(**query)
            .distinct()
            .select_related('terms_and_conditions')
            .prefetch_related('cover_picture__media')
        )

        if or_404:
            return get_object_or_404(queryset)
        else:
            return queryset.get()

    def __str__(self):
        return self.path

    def get_absolute_url(self):
        return f'{settings.EDEGAL_FRONTEND_URL}{self.path}'

    def get_descendants(self, include_self=False):
        ids = []
        self._get_descendants_into(ids)

        if include_self:
            ids.insert(0, self)

        return Album.objects.filter(id__in=ids)

    def get_ancestors(self, include_self=False):
        ids = []
        self._get_ancestors_into(ids)

        if include_self:
            ids.insert(0, self.id)

        return Album.objects.filter(id__in=ids)

    def get_family(self, include_self=False):
        ids = []

        self._get_ancestors_into(ids)

        if include_self:
            ids.insert(0, self.id)

        self._get_descendants_into(ids)

        return Album.objects.filter(id__in=ids)

    def _get_descendants_into(self, accumulator):
        subalbums = Album.objects.filter(parent=self).only('id')
        for subalbum in subalbums:
            accumulator.append(subalbum.id)
            subalbum._get_descendants(accumulator)

    def _get_ancestors_into(self, accumulator):
        album = self
        while album.parent_id:
            accumulator.append(album.parent_id)
            album = Album.objects.filter(id=album.parent_id).only('parent_id').get()

    class Meta:
        verbose_name = 'Album'
        verbose_name_plural = 'Albums'
        unique_together = [('parent', 'slug')]
