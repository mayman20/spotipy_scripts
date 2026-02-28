import { SpotifyUser, Script, Run } from './types';

export const mockUser: SpotifyUser = {
  id: 'alexrivera',
  displayName: 'Alex Rivera',
  email: 'alex@example.com',
  avatarUrl: 'https://api.dicebear.com/7.x/avataaars/svg?seed=alex',
  playlists: 47,
  savedTracks: 2341,
  following: 156,
};

export const scripts: Script[] = [
  {
    id: 'monthly-recommendations',
    name: 'Monthly Recommendations Playlist',
    description: 'Create a playlist with monthly top discoveries.',
    icon: 'Star',
    enabled: false,
    disabledReason: 'Temporarily unavailable while recommendations pipeline is being improved.',
    configFields: [
      { name: 'playlistName', label: 'Playlist Name', type: 'text', placeholder: 'Monthly Discoveries - Feb 2026' },
      { name: 'trackCount', label: 'Number of Tracks', type: 'number', defaultValue: 30 },
      { name: 'includeExplicit', label: 'Include Explicit', type: 'toggle', defaultValue: true },
    ],
  },
  {
    id: 'liked-songs-mirror',
    name: 'Liked Songs Mirror',
    description: 'Mirror liked songs into a playlist for easier sorting.',
    icon: 'Heart',
    configFields: [
      { name: 'targetPlaylist', label: 'Target Playlist', type: 'select', options: ['Create New', 'Liked Songs Mirror', 'My Collection'] },
      { name: 'syncInterval', label: 'Sync Mode', type: 'select', options: ['One-time', 'Daily', 'Weekly'] },
    ],
  },
  {
    id: 'archive-old-playlists',
    name: 'Archive Old Playlists',
    description: 'Move playlists older than X months into an Archive folder.',
    icon: 'Archive',
    configFields: [
      { name: 'monthsThreshold', label: 'Months Threshold', type: 'number', defaultValue: 6 },
      { name: 'archivePrefix', label: 'Archive Prefix', type: 'text', placeholder: '[Archive]' },
    ],
  },
  {
    id: 'vaulted-add',
    name: 'Vaulted Add',
    description: 'Add songs meeting conditions to a "Vaulted" playlist.',
    icon: 'Lock',
    configFields: [
      { name: 'minPlays', label: 'Minimum Plays', type: 'number', defaultValue: 50 },
      { name: 'targetPlaylist', label: 'Vault Playlist', type: 'select', options: ['Create New', 'The Vault', 'Favorites Vault'] },
      { name: 'autoRemove', label: 'Auto-remove from source', type: 'toggle', defaultValue: false },
    ],
  },
];

export const mockRuns: Run[] = [
  {
    id: 'run-001',
    scriptId: 'monthly-recommendations',
    scriptName: 'Monthly Recommendations Playlist',
    status: 'succeeded',
    startedAt: '2026-02-27T10:30:00Z',
    duration: '12s',
    logsPreview: 'Found 30 tracks. Playlist created successfully.',
  },
  {
    id: 'run-003',
    scriptId: 'liked-songs-mirror',
    scriptName: 'Liked Songs Mirror',
    status: 'failed',
    startedAt: '2026-02-26T15:45:00Z',
    duration: '3s',
    logsPreview: 'Error: Rate limit exceeded. Retry in 30s.',
  },
  {
    id: 'run-004',
    scriptId: 'archive-old-playlists',
    scriptName: 'Archive Old Playlists',
    status: 'queued',
    startedAt: '2026-02-27T11:05:00Z',
    duration: '—',
    logsPreview: 'Waiting in queue...',
  },
  {
    id: 'run-005',
    scriptId: 'vaulted-add',
    scriptName: 'Vaulted Add',
    status: 'succeeded',
    startedAt: '2026-02-25T09:00:00Z',
    duration: '8s',
    logsPreview: 'Added 15 tracks to The Vault.',
  },
];
