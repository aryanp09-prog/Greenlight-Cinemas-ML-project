import pandas as pd 
import ast 

def load_and_clean_movies(path: str) -> pd.DataFrame:
    movies = pd.read_csv(path, low_memory=False)
    for col in ['budget', 'revenue', 'popularity', 'id']:
        movies[col] = pd.to_numeric(movies[col], errors='coerce')
    movies['release_date']  = pd.to_datetime(movies['release_date'], errors='coerce')
    movies['release_year']  = movies['release_date'].dt.year
    movies['release_month'] = movies['release_date'].dt.month
    movies['genre_list']    = movies['genres'].apply(_parse_genres)
    return movies

def _parse_genres(x) -> list[str]:
    try:
        return[d['name'] for d in ast.literal_eval(x)] if isinstance(x,str) else[]
    except(ValueError, SyntaxError):
        return[]