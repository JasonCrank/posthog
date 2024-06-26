# Generated by Django 3.2.5 on 2022-03-01 23:41
from typing import Any, List, Tuple

from django.core.paginator import Paginator
from django.db import migrations
from django.db.models import Q

from posthog.models.tag import tagify


def forwards(apps, schema_editor):
    import structlog

    logger = structlog.get_logger(__name__)
    logger.info("posthog/0219_migrate_tags_v2_start")

    Tag = apps.get_model("posthog", "Tag")
    TaggedItem = apps.get_model("posthog", "TaggedItem")
    Insight = apps.get_model("posthog", "Insight")
    Dashboard = apps.get_model("posthog", "Dashboard")

    createables: List[Tuple[Any, Any]] = []
    batch_size = 1_000

    # Collect insight tags and taggeditems
    insight_paginator = Paginator(
        Insight.objects.exclude(
            Q(deprecated_tags__isnull=True) | Q(deprecated_tags=[]),
        )
        .order_by("created_at")
        .values_list("deprecated_tags", "team_id", "id"),
        batch_size,
    )

    for insight_page in insight_paginator.page_range:
        logger.info(
            "insight_tag_batch_get_start",
            limit=batch_size,
            offset=(insight_page - 1) * batch_size,
        )
        insights = iter(insight_paginator.get_page(insight_page))
        for tags, team_id, insight_id in insights:
            unique_tags = {tagify(t) for t in tags if isinstance(t, str) and t.strip() != ""}
            for tag in unique_tags:
                temp_tag = Tag(name=tag, team_id=team_id)
                createables.append((temp_tag, TaggedItem(insight_id=insight_id, tag_id=temp_tag.id)))

    logger.info("insight_tag_get_end", tags_count=len(createables))
    num_insight_tags = len(createables)

    # Collect dashboard tags and taggeditems
    dashboard_paginator = Paginator(
        Dashboard.objects.exclude(
            Q(deprecated_tags__isnull=True) | Q(deprecated_tags=[]),
        )
        .order_by("created_at")
        .values_list("deprecated_tags", "team_id", "id"),
        batch_size,
    )

    for dashboard_page in dashboard_paginator.page_range:
        logger.info(
            "dashboard_tag_batch_get_start",
            limit=batch_size,
            offset=(dashboard_page - 1) * batch_size,
        )
        dashboards = iter(dashboard_paginator.get_page(dashboard_page))
        for tags, team_id, dashboard_id in dashboards:
            unique_tags = {tagify(t) for t in tags if isinstance(t, str) and t.strip() != ""}
            for tag in unique_tags:
                temp_tag = Tag(name=tag, team_id=team_id)
                createables.append(
                    (
                        temp_tag,
                        TaggedItem(dashboard_id=dashboard_id, tag_id=temp_tag.id),
                    )
                )

    logger.info("dashboard_tag_get_end", tags_count=len(createables) - num_insight_tags)

    # Consistent ordering to make independent runs non-deterministic
    createables = sorted(createables, key=lambda pair: pair[0].name)

    # Attempts to create tags in bulk while ignoring conflicts. bulk_create does not return any data
    # about which tags were ignored and created, so we must take care of this manually.
    tags_to_create = [tag for (tag, _) in createables]
    Tag.objects.bulk_create(tags_to_create, ignore_conflicts=True, batch_size=batch_size)
    logger.info("tags_bulk_created")

    # Associate tag ids with tagged_item objects in batches. Best case scenario all tags are new. Worst case
    # scenario, all tags already exist and get is made for every tag.
    for offset in range(0, len(tags_to_create), batch_size):
        logger.info("tagged_item_batch_create_start", limit=batch_size, offset=offset)
        batch = tags_to_create[offset : (offset + batch_size)]

        # Find tags that were created, and not already existing
        created_tags = Tag.objects.in_bulk([t.id for t in batch])

        # Tags that are in `tags_to_create` but not in `created_tags` are tags that already exist
        # in the db and must be fetched individually.
        createable_batch = createables[offset : (offset + batch_size)]
        for tag, tagged_item in createable_batch:
            if tag.id in created_tags:
                tagged_item.tag_id = created_tags[tag.id].id
            else:
                tagged_item.tag_id = Tag.objects.filter(name=tag.name, team_id=tag.team_id).first().id

        # Create tag <-> item relationships, ignoring conflicts
        TaggedItem.objects.bulk_create(
            [tagged_item for (_, tagged_item) in createable_batch],
            ignore_conflicts=True,
            batch_size=batch_size,
        )

    logger.info("posthog/0219_migrate_tags_v2_end")


def reverse(apps, schema_editor):
    TaggedItem = apps.get_model("posthog", "TaggedItem")
    TaggedItem.objects.filter(Q(dashboard_id__isnull=False) | Q(insight_id__isnull=False)).delete()
    # Cascade deletes tag objects


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("posthog", "0218_uniqueness_constraint_tagged_items"),
    ]

    operations = [migrations.RunPython(forwards, reverse, elidable=True)]
