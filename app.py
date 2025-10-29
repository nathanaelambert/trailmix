from dash import Dash, html

app = Dash(__name__)

GA_TAG = 'G-3R4901JN3H'

app.index_string = """
<!DOCTYPE html>
<html>
  <head>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-3R4901JN3H"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-3R4901JN3H');
    </script>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
  </head>
  <body>
    {%app_entry%}
    <footer>
      {%config%}
      {%scripts%}
      {%renderer%}
    </footer>
  </body>
</html>
"""

app.layout = html.Div([
    html.H1('CULINAIRE'),
    html.P('Dash, Render')
])

if __name__ == '__main__':
    app.run(debug=False)
