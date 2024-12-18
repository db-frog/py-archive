from pydantic import BaseModel, Field, BeforeValidator
from enum import Enum
from typing import Optional, List, Annotated

PyObjectId = Annotated[str, BeforeValidator(str)]

class AgeEnum(str, Enum):
    eighteen_to_twentyfour = "18-24"
    twentyfive_to_thirtyfour = "25-34"
    thirtyfive_to_fortyfour = "35-44"
    fortyfive_to_fiftyfour = "45-54"
    fiftyfive_to_sixtyfour = "55-64"
    sixtyfive_plus = "65+"

    def reprJSON(self):
        return self.value

class Location(BaseModel):
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    geolocation: Optional[str]
    def reprJSON(self):
        return dict(city=self.city, state=self.state, country=self.country, geolocation=self.geolocation)

class Contributor(BaseModel):
    name: str
    age_bucket: AgeEnum
    gender: Optional[str]
    ethnicity: str
    nationality: Optional[str]
    languages_spoken: List[str]
    occupation: Optional[str]

    def reprJSON(self):
        return dict(name=self.name, age_bucket=self.age_bucket, gender=self.gender, ethnicity=self.ethnicity,
                    nationality=self.nationality, languages_spoken=self.languages_spoken, occupation=self.occupation)

class Collector(BaseModel):
    name: str
    gender: Optional[str]
    # should be semester
    collector_comments: str

    def reprJSON(self):
        return dict(name=self.name, gender=self.gender, semester=self.semester)

class Context(BaseModel):
    use_context: Optional[str]
    cultural_background: Optional[str]
    collection_context: Optional[str]

    def reprJSON(self):
        return dict(use_context=self.use_context, cultural_background=self.cultural_background,
                    collection_context=self.collection_context)

class Analysis(BaseModel):
    context: Context
    interpretation: Optional[str]
    collector_comments: Optional[str]

    def reprJSON(self):
        return dict(context=self.context, interpretation=self.interpretation,
                    collector_comments=self.collector_comments)

class Folklore(BaseModel):
    item: str
    genre: str
    language_of_origin: Optional[str]
    medium: str
    translation: Optional[str]
    place_mentioned: List[Location]

    def reprJSON(self):
        return dict(item=self.item, genre=self.genre, language_of_origin=self.language_of_origin,
                    medium=self.medium, translation=self.translation, place_mentioned=self.place_mentioned)

class FolkloreCollection(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    filename: Optional[str]
    contributor: Contributor
    folklore: Folklore
    collector: Collector
    analysis: Analysis
    storage_medium: str
    cleaned_full_text: str
    date_collected: str
    location_collected: Location

    def reprJSON(self):
        return dict(filename=self.filename, contributor=self.contributor, folklore=self.folklore,
                    collector=self.collector,
                    analysis=self.analysis, storage_medium=self.storage_medium,
                    cleaned_full_text=self.cleaned_full_text,
                    date_collected=self.date_collected, location_collected=self.location_collected)
