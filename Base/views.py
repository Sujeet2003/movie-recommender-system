import pickle
import random
import requests
from requests.exceptions import RequestException
from django.core.cache import cache  # Django cache framework
from django.shortcuts import render, redirect
import gdown
# Create your views here.

# similarity_matrix
file_id = "1ipGtc8xlzGeLh8iwDqfL7wCCSRVIqeL8"
url = f"https://drive.google.com/uc?id={file_id}"
output = 'matrix.pkl'
gdown.download(url, output, quiet=False)

# Load the pickle file
with open(output, 'rb') as f:
    similarity_matrix = pickle.load(f)

# manually added similarity_matrix
# similarity_matrix = pickle.load(open('C:/Users/sujee/Desktop/Project/MovieRecommender/similarity_matrix.pkl', 'rb'))

# Load data
def get_movie_data():
    if 'movie_data' not in cache:
        load_movie = pickle.load(open('movies.pkl', 'rb'))
        cache.set('movie_data', load_movie, 60 * 60)
    return cache.get('movie_data')

movie_list = get_movie_data()  # Cached data for movie list

# Fetching poster for each movie
def fetch_poster(movie_id):
    cache_key = f"poster_{movie_id}"
    cached_poster = cache.get(cache_key)
    if cached_poster:
        return cached_poster

    try:
        response = requests.get(
            f'https://api.themoviedb.org/3/movie/{movie_id}?api_key=e46c5d37f787329f477b6606a4246fce&language=en-US'
        )
        response.raise_for_status()
        poster_path = response.json().get('poster_path')

        if poster_path:
            full_path = "https://image.tmdb.org/t/p/w500" + poster_path
            cache.set(cache_key, full_path, 60 * 60)
            return full_path
    except RequestException as e:
        print(f"Error fetching poster for movie ID {movie_id}: {e}")

    return None

# Getting all details about movies using movie_id
def other_details(movie_id):
    cache_key = f"details_{movie_id}"
    cached_details = cache.get(cache_key)
    if cached_details:
        return cached_details

    try:
        response = requests.get(
            f'https://api.themoviedb.org/3/movie/{movie_id}?api_key=e46c5d37f787329f477b6606a4246fce&language=en-US'
        )
        response.raise_for_status()
        data = response.json()

        overview = data.get('overview', 'N/A')
        genres_list = [genre['name'] for genre in data.get('genres', [])]
        release_date = data.get('release_date', 'N/A')
        lang_list = [lang['english_name'] for lang in data.get('spoken_languages', [])]
        runtime = data.get('runtime', 'N/A')
        rating = data.get('vote_average', 'N/A')
        vote_count = data.get('vote_count', 'N/A')

        details = (overview, genres_list, release_date, lang_list, runtime, rating, vote_count)
        cache.set(cache_key, details, 60 * 60)
        return details
    except RequestException as e:
        print(f"Error fetching details for movie ID {movie_id}: {e}")
    return None

# Getting movie_id using movie_name from inputs
def recommend(movie_name):
    cache_key = f"recommend_{movie_name}"
    cached_recommendations = cache.get(cache_key)
    if cached_recommendations:
        return cached_recommendations

    try: 
        movie_index = movie_list[movie_list['title'] == movie_name].index[0]
        distances = similarity_matrix[movie_index]
        movies_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

        recommended_movies = []
        recommended_movies_poster = []
        movies_details = []

        for movie in movies_list:
            movie_id = movie_list.iloc[movie[0]].id
            recommended_movies_poster.append(fetch_poster(movie_id))
            movies_details.append(other_details(movie_id))
            recommended_movies.append(movie_list.iloc[movie[0]].title)

        result = (recommended_movies, recommended_movies_poster, movies_details)
        cache.set(cache_key, result, 60 * 60) 
        return result

    except Exception as e:
        print(f"Error in recommendation process: {e}")
        return [], [], []

# home page
def home(request):
    movie_list_data = get_movie_data()
    movies_list = [movie for movie in movie_list_data['title']]
    recommended_movies, recommended_movies_poster, list_of_each_movie_details = [], [], []

    if request.method == "POST":
        movie_name = request.POST.get('movie_name')
        try:
            recommended_movies, recommended_movies_poster, movies_details = recommend(movie_name)
        except Exception as e:
            print(f"Error while recommending: {e}")
            return redirect('home')

        request.session['movie_name'] = movie_name
        request.session['recommended_movies'] = recommended_movies
        request.session['recommended_movies_poster'] = recommended_movies_poster
        request.session['movies_details'] = movies_details

        list_of_each_movie_details = [
            {'overview': detail[0], 'genres': detail[1], 'release_date': detail[2], 'languages': detail[3], 'duration': detail[4], 'rating': detail[5], 'total_votes': detail[6]}
            for detail in movies_details if detail is not None 
        ]

        request.session['list_of_each_movie_details'] = list_of_each_movie_details
        return redirect('home')

    movie_name = request.session.pop('movie_name', '')
    recommended_movies = request.session.pop('recommended_movies', [])
    recommended_movies_poster = request.session.pop('recommended_movies_poster', [])
    list_of_each_movie_details = request.session.pop('list_of_each_movie_details', [])

    combined_data = list(zip(recommended_movies_poster, recommended_movies, list_of_each_movie_details))
    images_path = random_id_generator_for_images()
    active_image_path = images_path[0] if images_path else ""

    descriptions = descriptions_about_project()

    context = {
        'movie_name': movie_name,
        'combined_data': combined_data,
        'movies_list': movies_list,
        'active_image_path': active_image_path,
        'images_path': images_path[1:] if len(images_path) > 1 else [],
        'descriptions': descriptions,
    }

    return render(request, 'index.html', context)


# Generating path for carousel images
def random_id_generator_for_images():
    path = []
    max_attempts = 20
    attempts = 0

    while len(path) < 5 and attempts < max_attempts:
        random_movie_id = random.randint(1500, 2000)
        try:
            response = requests.get(
                f'https://api.themoviedb.org/3/movie/{random_movie_id}?api_key=e46c5d37f787329f477b6606a4246fce&language=en-US'
            )
            response.raise_for_status()
            movie_data = response.json()
            
            poster = movie_data.get('poster_path')
            if isinstance(poster, str):
                path.append("https://image.tmdb.org/t/p/w500" + poster)
                print(f"Added poster path for movie ID {random_movie_id}: {poster}")
            else:
                print(f"No poster found for movie ID {random_movie_id}. Skipping.")
        
        except RequestException as e:
            print(f"Request failed for movie ID {random_movie_id}: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

        attempts += 1

    if len(path) < 5:
        print(f"Only {len(path)} poster paths could be retrieved after {attempts} attempts.")
    return path


# descriptions and introduction about project
def descriptions_about_project():
    introduction = '''In today's digital age, where the sheer volume of available movies can overwhelm even the most avid cinephile, a movie recommender system becomes indispensable. "The Movie Recommender Hub" is a project designed to streamline the process of movie selection, offering personalized recommendations to users based on their preferences and viewing history. The project leverages sophisticated data science techniques, including feature engineering and cosine similarity metrics, to deliver accurate and relevant movie suggestions.'''

    data_collection_and_preprocessing = '''The foundation of any recommender system is the quality of the data it uses. For The Movie Recommender Hub, data was sourced from Kaggle, a well-known platform that hosts datasets across various domains, including movies. The dataset included a wealth of information such as movie titles, genres, ratings, and user interactions. However, raw data is rarely in a form suitable for immediate analysis.
    Data preprocessing involved several steps. First, any missing or inconsistent data was handled. Missing values, which can distort the accuracy of the recommendations, were either filled with appropriate values or removed if deemed insignificant. Duplicates were identified and eliminated to ensure that each movie was uniquely represented.
    Next, the data was normalized and standardized to ensure uniformity across all features. For instance, categorical data, such as genres, was encoded into numerical values that could be easily processed by the model. Additionally, the dataset was split into training and testing sets to facilitate model evaluation.'''

    feature_engineering = '''Feature engineering is a critical step in enhancing the performance of machine learning models. In the context of The Movie Recommender Hub, feature engineering involved creating new features from existing ones to capture more information about the movies. This process improves the model's ability to discern between different movies and their appeal to various users.
    One of the key features engineered was the creation of a genre vector for each movie. Movies often belong to multiple genres, and representing these genres as a vector allows the model to understand the similarities and differences between movies in a more granular way. For example, a movie that belongs to both "Action" and "Thriller" will have a different vector than a movie that belongs to "Action" and "Comedy," even though they share one genre.'''

    machine_learning_used = '''To recommend movies that are most similar to what a user has already enjoyed, The Movie Recommender Hub employs cosine similarity metrics. Cosine similarity is a measure of the cosine of the angle between two vectors, which in this case represent movies. It quantifies how similar two movies are based on their feature vectors.
    The advantage of using cosine similarity is that it is not affected by the magnitude of the vectors, making it particularly useful in scenarios where the length of the vectors (such as the number of genres a movie belongs to) may vary. Instead, cosine similarity focuses on the direction of the vectors, ensuring that movies with similar content are grouped together, regardless of their individual characteristics.'''

    model_development_and_training = '''The core of The Movie Recommender Hub is the machine learning model that processes the data and generates recommendations. After feature engineering and the application of cosine similarity metrics, the next step was to train the model using the training set. The model was designed to predict which movies a user is likely to enjoy based on their past interactions and the similarity of those movies to others in the dataset.'''

    deployment_and_ui = '''Once the model was trained and validated, the next step was to deploy it into a user-friendly interface. The Movie Recommender Hub was designed with the end-user in mind, ensuring that the system is intuitive and easy to navigate. Users can enter the name of a movie they like, and the system will generate a list of recommended movies along with relevant details such as genre, release year, and a brief synopsis.'''

    conclusion = '''The Movie Recommender Hub represents a significant advancement in personalized movie recommendation systems. By leveraging sophisticated data science techniques such as feature engineering and cosine similarity metrics, the project has succeeded in creating a system that delivers highly accurate and relevant movie suggestions.'''

    context = {
        'introduction': introduction,
        'data_collection_and_preprocessing': data_collection_and_preprocessing,
        'feature_engineering': feature_engineering,
        'machine_learning_used': machine_learning_used,
        'model_development_and_training': model_development_and_training,
        'deployment_and_ui': deployment_and_ui,
        'conclusion': conclusion
    }
    return context