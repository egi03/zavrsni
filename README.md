# Music Recommendation System

A sophisticated Django-based music recommendation platform that leverages machine learning to provide personalized song suggestions. The system integrates with Spotify and Last.fm APIs to deliver intelligent music discovery experiences.

![Django](https://img.shields.io/badge/django-%23092E20.svg?style=for-the-badge&logo=django&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-%23FF6F00.svg?style=for-the-badge&logo=TensorFlow&logoColor=white)
![Spotify](https://img.shields.io/badge/Spotify-1ED760?style=for-the-badge&logo=spotify&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)

## Key Features

### Advanced Recommendation Engine
- **Multiple Algorithms**: Collaborative filtering, content-based, and hybrid approaches
- **TensorFlow Integration**: Neural collaborative filtering for user-item interactions
- **Strategy Selection**: Balanced, Discovery, and Popular recommendation modes
- **Real-time Generation**: Dynamic recommendation updates based on user behavior

### Music Integration
- **Spotify API**: OAuth authentication, playlist import, track metadata
- **Last.fm Integration**: Enhanced music metadata, tags, and similarity data
- **Audio Features**: Tempo, energy, danceability, acousticness analysis
- **Song Search**: Over 100 milion songs available

### Social Platform
- **User Profiles**: Customizable profiles with profile picture upload
- **Follow System**: User-to-user following with activity feeds
- **Real-time Messaging**: AJAX-powered instant messaging system
- **Activity Tracking**: Social feed showing user interactions
- **Playlist Sharing**: Public/private playlist management

### Modern UI/UX
- **Responsive Design**: Mobile-first approach with smooth animations
- **Interactive Elements**: Hover effects, loading states, and micro-interactions
- **Real-time Updates**: Dynamic content loading without page refreshes
- **Custom Cursor Effects**: Enhanced user experience with particle trails
- **Progressive Enhancement**: Graceful degradation for accessibility

## Technical Architecture

### Backend Technologies
```python
# Core Framework
Django 5.1.6              # Web framework
TensorFlow 2.x            # Machine learning
Spotipy                   # Spotify API client
Requests                  # HTTP client for Last.fm

# Database & Storage
SQLite3                   # Development database
Pillow                    # Image processing
```

### Machine Learning Components
- **Neural Collaborative Filtering**: Matrix factorization with deep learning
- **Content-Based Filtering**: Audio feature similarity and tag matching
- **Hybrid Recommender**: Weighted combination of multiple approaches
- **Feature Engineering**: Audio analysis and music metadata processing

### API Integrations
- **Spotify Web API**: Track data, playlists, audio features
- **Last.fm API**: Music metadata, tags, artist information
- **OAuth 2.0**: Secure third-party authentication, for importing playlists

## Project Structure

<details>
<summary>Click to expand project structure</summary>

```
zavrsni/
├── 📁 accounts/           # User management & authentication
│   ├── models.py         # UserProfile model
│   ├── forms.py          # Custom authentication forms
│   ├── views.py          # Profile management views
│   └── templates/        # User interface templates
├── 📁 music/             # Core music functionality
│   ├── models.py         # Song, Playlist models
│   ├── views.py          # Playlist management
│   └── templates/        # Music interface templates
├── 📁 recommendations/   # ML recommendation engine
│   ├── collaborative_recommender.py  # Neural collaborative filtering
│   ├── content_recommender.py        # Content-based recommendations
│   ├── hybrid_recommender.py         # Hybrid approach
│   ├── models.py         # Recommendation storage
│   └── management/       # Training commands
├── 📁 social/            # Social features
│   ├── models.py         # Follow, Message, Activity models
│   ├── views.py          # Social interactions
│   └── templates/        # Social interface
├── 📁 spotify/           # Spotify integration
│   ├── models.py         # Token management
│   ├── utils.py          # API wrapper classes
│   └── views.py          # OAuth flow
├── 📁 lastfm/            # Last.fm integration
│   └── utils.py          # Music metadata enrichment
└── 📁 static/            # Frontend assets
    ├── styles/           # CSS stylesheets
    └── scripts/          # JavaScript modules
```
</details>

# Machine Learning Implementation

## Thre Recommendation Options

The system implements a sophisticated **hybrid recommendation engine** that combines multiple machine learning approaches to provide personalized music suggestions:

### 1. **Collaborative Filtering** - "Users who liked this also liked..."
### 2. **Content-Based Filtering** - "Songs similar to what you already enjoy"
### 3. **Hybrid Ensemble** - "Best of both worlds with strategic weighting"

---

## 1. Neural Collaborative Filtering

### Core Concept
Uses **deep learning** to find hidden patterns in user-item interactions. Instead of traditional matrix factorization, it employs neural networks to learn complex, non-linear relationships.

**How it works:**
- Converts playlists and songs into dense vector representations (embeddings)
- Learns which playlists and songs are similar in a shared mathematical space
- Predicts affinity scores between any playlist-song combination

```python
# Simplified core logic
def predict_affinity(playlist_embedding, song_embedding):
    similarity = dot_product(playlist_embedding, song_embedding)
    return similarity + playlist_bias + song_bias
```

### Mathematical Foundation
- **Input**: Playlist-song interaction matrix (sparse)
- **Output**: Dense embedding vectors for playlists and songs
- **Optimization**: Minimizes prediction error using gradient descent
- **Regularization**: L2 penalty prevents overfitting

### Training Data Structure
```
Playlist A: [Song1, Song3, Song5] → Rating: 1.0 (implicit feedback)
Playlist B: [Song2, Song3, Song4] → Rating: 1.0 (implicit feedback)
```

---

## 2. Content-Based Filtering

### Two-Component Approach

#### A) **Audio Feature Analysis**
Leverages Spotify's audio features to find musically similar songs:

```python
# Audio features used for similarity
audio_features = {
    'energy': 0.8,        # High energy songs
    'valence': 0.6,       # Positive/happy songs  
    'danceability': 0.7,  # Danceable tracks
    'acousticness': 0.2,  # Electronic vs acoustic
    'tempo': 128.0,       # BPM
    'instrumentalness': 0.1  # Vocal vs instrumental
}
```

**Similarity Calculation:**
- Euclidean distance between audio feature vectors
- Weighted importance based on user's playlist characteristics
- Normalization to 0-1 scale for consistent scoring

#### B) **Tag-Based Similarity (Last.fm Integration)**
Uses music metadata and user-generated tags:

```python
# Example tag weights from Last.fm
song_tags = {
    'rock': 0.9,
    'indie': 0.7, 
    'alternative': 0.8,
    'guitar': 0.6
}
```

**Tag Processing:**
- **Tag Weight Normalization**: Converts raw tag counts to probabilities
- **Similarity Metrics**: Jaccard coefficient and cosine similarity
- **Tag Boosting**: Popular genres get enhanced importance
- **Temporal Decay**: Newer tag data weighted more heavily

### Content Similarity Algorithm
```python
def calculate_similarity(song1, song2):
    # Audio feature similarity (40% weight)
    audio_sim = cosine_similarity(song1.audio_features, song2.audio_features)
    
    # Tag similarity (60% weight)  
    tag_sim = jaccard_similarity(song1.tags, song2.tags)
    
    return 0.4 * audio_sim + 0.6 * tag_sim
```

---

## 3. Hybrid Recommendation System

### Strategic Weighting

The system offers **three distinct strategies** that weight different approaches:

```python
STRATEGIES = {
    'balanced': {
        'collaborative': 40%,    # User behavior patterns
        'content_tags': 30%,     # Music metadata similarity
        'content_similar': 20%,  # Audio feature similarity  
        'popularity': 10%        # Trending factor
    },
    'discovery': {
        'collaborative': 20%,    # Less weight on existing patterns
        'content_tags': 50%,     # Heavy focus on music attributes
        'content_similar': 20%,  # Audio similarity
        'popularity': 10%        # Minimal popularity bias
    },
    'popular': {
        'collaborative': 10%,    # Minimal personalization
        'content_tags': 20%,     # Some content matching
        'content_similar': 10%,  # Basic similarity
        'popularity': 60%        # Heavy trending bias
    }
}
```

### Score Aggregation Process

1. **Individual Scoring**: Each algorithm generates scores (0-1) for candidate songs
2. **Normalization**: Scores normalized to prevent algorithm bias
3. **Weighted Combination**: Strategic weights applied based on user preference
4. **Final Ranking**: Combined scores sorted for top recommendations

```python
def calculate_hybrid_score(song, strategy='balanced'):
    scores = {
        'collaborative': get_collaborative_score(song),
        'content_tags': get_tag_similarity_score(song), 
        'content_similar': get_audio_similarity_score(song),
        'popularity': get_popularity_score(song)
    }
    
    weights = STRATEGIES[strategy]
    
    final_score = sum(scores[component] * weights[component] 
                     for component in scores.keys())
    
    return min(final_score, 1.0)  # Cap at 1.0
```

---

## Some of the features

### **Cold Start Problem Solutions**
- **New Users**: Rely heavily on popularity and content-based recommendations
- **New Songs**: Use audio features and artist similarity from Last.fm
- **Sparse Data**: Fallback to genre-based and trending recommendations

### **Real-time Learning**
- **Incremental Updates**: Model updates when users add songs to playlists
- **Feedback Integration**: User actions (adding recommended songs) improve future suggestions
- **Cache Invalidation**: Smart cache clearing when user preferences change

### **Performance Optimizations**
- **Batch Prediction**: Process multiple songs simultaneously using TensorFlow
- **Embedding Caching**: Store computed embeddings for faster lookup
- **Approximate Nearest Neighbors**: Use locality-sensitive hashing for large-scale similarity search

### **Quality Metrics**
- **Precision@K**: Percentage of recommended songs actually added by users
- **Diversity Score**: Ensures recommendations aren't too similar to each other
- **Coverage**: Percentage of song catalog that can be recommended
- **Novelty**: Balance between familiar and discovery-oriented suggestions

---

## Best Practices Demonstrated

### Code Organization
- **Separation of Concerns**: Clear app boundaries and responsibilities
- **DRY Principle**: Reusable components and utilities
- **Model Design**: Proper relationships and data integrity
- **View Logic**: Clean separation between business logic and presentation

### Security & Performance
- **Environment Variables**: Secure API key management
- **CSRF Protection**: Django's built-in security features
- **Caching Strategy**: Redis-like caching for recommendations
- **Database Optimization**: Efficient queries with select_related/prefetch_related

### Frontend Development
- **Progressive Enhancement**: JavaScript as enhancement, not requirement
- **Responsive Design**: Mobile-first CSS architecture
- **Performance**: Lazy loading and optimized assets
- **Accessibility**: Semantic HTML and ARIA attributes
- **Lighthouse test**: Gets 95/100 on Lighthouse test

### DevOps & Deployment
- **Docker Support**: Containerized development environment
- **Management Commands**: Automated data processing and model training
- **Logging**: Comprehensive error tracking and debugging

## Getting Started

### Prerequisites
```bash
Python 3.11+
Node.js 16+ (for frontend tooling)
Docker (optional)
```

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/music-recommendation-system.git
cd music-recommendation-system
```

2. **Set up environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
# Create .env file
SECRET_KEY=your-django-secret-key
DEBUG=True
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
LASTFM_API_KEY=your-lastfm-api-key
```

4. **Initialize database**
```bash
python manage.py migrate
python manage.py collectstatic
```

5. **Start development server**
```bash
python manage.py runserver
```

### Docker Setup
```bash
docker-compose up --build
```

## Management Commands

### Data Enrichment
```bash
# Enrich songs with Last.fm metadata
python manage.py enrich_songs_lastfm --batch-size 50

# Train recommendation models
python manage.py train_recommendations --model collaborative

# Update all recommendations
python manage.py update_recommendations --strategy balanced
```

## Usage Examples

### Creating Playlists
1. **Register/Login** to the platform
2. **Connect Spotify** account for playlist import ***(optional)***
3. **Create playlist** and add songs manually or import from Spotify
4. **Get recommendations** based on your music taste

### Recommendation Flow
1. **Add 3+ songs** to activate recommendation engine
2. **Choose strategy**: Balanced, Discovery, or Popular
3. **Review recommendations** with explanation scores
4. **Add songs** directly to your playlist

### Social Features
1. **Follow users** to see their activity
2. **Share playlists** publicly
3. **Comment** on public playlists
4. **Message** other users directly
---