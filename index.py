#!/usr/bin/env python

import os
import logging
import requests
import json
import configparser
import sys
import time

from syncarr.config import *

def get_new_content_payload(content, instance_path, instance_profile_id, instanceB_url):

    images = content.get('images')
    for image in images:
        image['url'] = '{0}{1}'.format(instanceB_url, image.get('url'))
        
    payload = {
        'title': content.get('title'),
        'titleSlug': content.get('titleSlug'),
        'images': images,
        'qualityProfileId': content.get('qualityProfileId'),
        'monitored': content.get('monitored'),
        'rootFolderPath': instance_path,
        content_id_key: content.get(content_id_key),
    }

    if is_sonarr:
        payload['seasons'] = content.get('seasons')
        payload['tvRageId'] = content.get('tvRageId')
        payload['seasonFolder'] = content.get('seasonFolder')
        payload['languageProfileId'] = content.get('languageProfileId')
        payload['tags'] = content.get('tags')
        payload['seriesType'] = content.get('seriesType')
        payload['useSceneNumbering'] = content.get('useSceneNumbering')
        payload['addOptions'] = content.get('addOptions')

    else:
        payload['minimumAvailability'] = content.get('minimumAvailability')
        payload['tmdbId'] = content.get('tmdbId')
        payload['year'] = content.get('year')
        payload['profileId'] = instance_profile_id

    logger.debug(payload)
    return payload


def get_content_path(instance_url, key):
    url = '{0}/{1}?apikey={2}'.format(instance_url, api_content_path, key)
    logger.debug('get_content_path: {}'.format(url))
    return url


def get_search_path(instance_url, key):
    url = '{0}/{1}?apikey={2}'.format(instance_url, api_search_path, key)
    logger.debug('get_search_path: {}'.format(url))
    return url


def sync_servers(instanceA_contents, instanceB_contentIds, instanceB_path, 
                 instanceB_profile_id, instanceB_session, instanceB_content_url, instanceB_url):

    search_ids = []

    for content in instanceA_contents:
        if content[content_id_key] not in instanceB_contentIds:
            logging.info('syncing content title "{0}"'.format(content.get('title')))

            payload = get_new_content_payload(content, instanceB_path, instanceB_profile_id, instanceB_url)
            sync_response = instanceB_session.post(instanceB_content_url, data=json.dumps(payload))

            if sync_response.status_code != 201 and sync_response.status_code != 200:
                logger.error('server sync error for {} - response {}'.format(content.get('title'), sync_response.status_code))
            else:
                search_ids.append(int(sync_response.json()['id']))
                logging.info('content title "{0}" synced successfully'.format(content.get('title')))
            
    return search_ids


def search_synced(search_ids, instanceB_search_url, instanceB_session):
    # now that we've synced all contents search for the newly synced contents
    logging.info('{} contents synced successfully'.format(len(search_ids)))
    if len(search_ids):
        payload = { 'name': 'contentsSearch', 'contentIds': search_ids }
        instanceB_session.post(instanceB_search_url, data=json.dumps(payload))


def sync_content():

    # get sessions
    instanceA_session = requests.Session()
    instanceA_session.trust_env = False
    instanceA_content_url = get_content_path(instanceA_url, instanceA_key)
    instanceA_contents = instanceA_session.get(instanceA_content_url)
    if instanceA_contents.status_code != requests.codes.ok:
        logger.error('instanceA server error - response {}'.format(instanceA_contents.status_code))
        sys.exit(0)
    else:
        instanceA_contents = instanceA_contents.json()

    instanceB_session = requests.Session()
    instanceB_session.trust_env = False
    instanceB_content_url = get_content_path(instanceB_url, instanceB_key)
    instanceB_search_url = get_search_path(instanceB_url, instanceB_key)
    instanceB_contents = instanceB_session.get(instanceB_content_url)
    if instanceB_contents.status_code != requests.codes.ok:
        logger.error('instanceB server error - response {}'.format(instanceB_contents.status_code))
        sys.exit(0)
    else:
        instanceB_contents = instanceB_contents.json()


    # get all contentIds from instances so we can keep track of what contents already exist
    instanceA_contentIds = []
    for content_to_sync in instanceA_contents:
        instanceA_contentIds.append(content_to_sync[content_id_key])
    logger.debug('{} contents in instanceA'.format(len(instanceA_contentIds)))

    instanceB_contentIds = []
    for content_to_sync in instanceB_contents:
        instanceB_contentIds.append(content_to_sync[content_id_key])
    logger.debug('{} contents in instanceB'.format(len(instanceB_contentIds)))


    # sync content from instanceA to instanceB
    logger.info('syncing content from instance A to instance B')
    search_ids = sync_servers(
        instanceA_contents, instanceB_contentIds, instanceB_path, 
        instanceB_profile_id, instanceB_session, instanceB_content_url, instanceB_url
    )
    search_synced(search_ids, instanceB_search_url, instanceB_session)


    # if given bidirectional flag then sync from instance B to instance A
    if sync_bidirectionally:
        logger.info('syncing content from instance B to instance A')
        search_ids = sync_servers(
            instanceB_contents, instanceA_contentIds, instanceA_path, 
            instanceA_profile_id, instanceA_session, instanceA_content_url, instanceA_url
        )
        search_synced(search_ids, instanceA_search_url, instanceA_session)


if is_in_docker:
    logger.info('syncing every {} seconds'.format(instance_sync_interval_seconds))

sync_content()

if is_in_docker:
    while True:
        time.sleep(instance_sync_interval_seconds)
        sync_content()
