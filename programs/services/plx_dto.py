from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ProgramInfoDTO:
    education_level_name: str
    training_direction_code: str
    training_direction_name: str
    profile_code: str
    profile_name: str
    admission_year: int

    def to_dict(self) -> dict:
        return {
            'education_level_name': self.education_level_name,
            'training_direction_code': self.training_direction_code,
            'training_direction_name': self.training_direction_name,
            'profile_code': self.profile_code,
            'profile_name': self.profile_name,
            'admission_year': self.admission_year,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ProgramInfoDTO':
        return cls(
            education_level_name=data['education_level_name'],
            training_direction_code=data['training_direction_code'],
            training_direction_name=data['training_direction_name'],
            profile_code=data['profile_code'],
            profile_name=data['profile_name'],
            admission_year=int(data['admission_year']),
        )


@dataclass(slots=True)
class DepartmentInfoDTO:
    number: str
    short_name: str
    full_name: str

    def to_dict(self) -> dict:
        return {
            'number': self.number,
            'short_name': self.short_name,
            'full_name': self.full_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DepartmentInfoDTO':
        return cls(
            number=data['number'],
            short_name=data['short_name'],
            full_name=data['full_name'],
        )


@dataclass(slots=True)
class DisciplineDTO:
    external_id: str
    code: str
    name: str

    def to_dict(self) -> dict:
        return {
            'external_id': self.external_id,
            'code': self.code,
            'name': self.name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DisciplineDTO':
        return cls(
            external_id=data['external_id'],
            code=data['code'],
            name=data['name'],
        )


@dataclass(slots=True)
class CompetenceDTO:
    external_id: str
    code: str
    name: str
    competence_type_name: str

    def to_dict(self) -> dict:
        return {
            'external_id': self.external_id,
            'code': self.code,
            'name': self.name,
            'competence_type_name': self.competence_type_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CompetenceDTO':
        return cls(
            external_id=data['external_id'],
            code=data['code'],
            name=data['name'],
            competence_type_name=data['competence_type_name'],
        )


@dataclass(slots=True)
class DisciplineCompetenceLinkDTO:
    discipline_external_id: str
    competence_external_id: str

    def to_dict(self) -> dict:
        return {
            'discipline_external_id': self.discipline_external_id,
            'competence_external_id': self.competence_external_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DisciplineCompetenceLinkDTO':
        return cls(
            discipline_external_id=data['discipline_external_id'],
            competence_external_id=data['competence_external_id'],
        )


@dataclass(slots=True)
class PlxProgramImportDTO:
    source_filename: str
    program: ProgramInfoDTO
    department: DepartmentInfoDTO
    disciplines: list[DisciplineDTO] = field(default_factory=list)
    competences: list[CompetenceDTO] = field(default_factory=list)
    discipline_competence_links: list[DisciplineCompetenceLinkDTO] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'source_filename': self.source_filename,
            'program': self.program.to_dict(),
            'department': self.department.to_dict(),
            'disciplines': [item.to_dict() for item in self.disciplines],
            'competences': [item.to_dict() for item in self.competences],
            'discipline_competence_links': [
                item.to_dict() for item in self.discipline_competence_links
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PlxProgramImportDTO':
        return cls(
            source_filename=data['source_filename'],
            program=ProgramInfoDTO.from_dict(data['program']),
            department=DepartmentInfoDTO.from_dict(data['department']),
            disciplines=[DisciplineDTO.from_dict(item) for item in data['disciplines']],
            competences=[CompetenceDTO.from_dict(item) for item in data['competences']],
            discipline_competence_links=[
                DisciplineCompetenceLinkDTO.from_dict(item)
                for item in data['discipline_competence_links']
            ],
        )

    def summary(self) -> dict:
        return {
            'source_filename': self.source_filename,
            'education_level': self.program.education_level_name,
            'training_direction': f'{self.program.training_direction_code} — {self.program.training_direction_name}',
            'profile': f'{self.program.profile_code} — {self.program.profile_name}',
            'department': f'{self.department.number} — {self.department.short_name}',
            'admission_year': self.program.admission_year,
            'disciplines_count': len(self.disciplines),
            'competences_count': len(self.competences),
            'links_count': len(self.discipline_competence_links),
        }

