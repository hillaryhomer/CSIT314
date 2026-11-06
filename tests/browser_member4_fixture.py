"""Real project fixtures for Member 4's isolated browser database only."""
import base64
from io import BytesIO
import os
from pathlib import Path

from PIL import Image
from backend.database import connect_database, Repository
from backend.project_controllers import CreateCurrentIDPController, CreatePastIDPController

filename = Path(os.environ['DATABASE_PATH']).resolve()
if filename.parent != Path('.test-data').resolve() or not filename.name.startswith('python-browser-'):
    raise RuntimeError('Customer browser fixtures require a dedicated test database.')
connection = connect_database(str(filename))
try:
    repository = Repository(connection)
    data = BytesIO(); Image.new('RGB', (4, 4), 'blue').save(data, format='PNG')
    image = {'data': base64.b64encode(data.getvalue()).decode(), 'mimeType': 'image/png'}
    for controller, title, description, category, style, images in [
        (CreateCurrentIDPController, 'Coastal Loft', 'Calm coastal interiors', 'CAT001', 'Japandi', [image]),
        (CreatePastIDPController, 'City Cafe', 'Calm coastal hospitality', 'CAT003', 'Modern', []),
        (CreateCurrentIDPController, 'Work Studio', 'Practical workspaces', 'CAT002', 'Japandi', []),
        (CreatePastIDPController, 'Garden Home', 'Green family interiors', 'CAT001', 'Modern', []),
    ]:
        controller(repository, 'browser-designer').execute(dict(title=title, description=description, categoryId=category, style=style, images=images))
finally:
    connection.close()
