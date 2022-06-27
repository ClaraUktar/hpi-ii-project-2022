from build.gen.bakdata.corporate.v2.cleaned_company_pb2 import CleanedCompany
from build.gen.bakdata.corporate.v2.company_pb2 import Company


class CompanyStandardizer:
    def clean_company(self, company: Company) -> CleanedCompany:
        # TODO: Add cleaning logic
        cleaned_company = CleanedCompany()

        cleaned_company.name = company.name
        cleaned_company.address = company.address
        cleaned_company.country = company.country
        cleaned_company.description = company.description
        cleaned_company.capital = company.capital

        return cleaned_company
