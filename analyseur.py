MOIS_FR = {
    1: 'Janvier', 2: 'Février',  3: 'Mars',     4: 'Avril',
    5: 'Mai',     6: 'Juin',     7: 'Juillet',   8: 'Août',
    9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
}


class AnalyseurDepenses:
    """
    지출 데이터를 분석하는 클래스.

    사용법:
        analyseur = AnalyseurDepenses(donnees)
        categories = analyseur.analyser_categories()
    """

    def __init__(self, donnees):
        self.donnees  = donnees
        # 지출만 / 수입만 따로 분리 (자주 씀)
        self.depenses = donnees[donnees['Montant'] < 0].copy()
        self.revenus  = donnees[donnees['Montant'] > 0].copy()

    def analyser_categories(self):
        """
        카테고리별 지출 합계와 비율을 계산합니다. (전체 기간 합산)
        반환값: {'Transport': {'total': 250.0, 'pourcentage': 15.5}, ...}
        """
        par_categorie  = self.depenses.groupby('Catégorie')['Montant_abs'].sum()
        total_depenses = par_categorie.sum()

        resultats = {}
        for categorie, montant in par_categorie.items():
            resultats[categorie] = {
                'total': round(montant, 2),
                'pourcentage': round((montant / total_depenses) * 100, 1)
            }
        return resultats

    def analyser_categories_par_mois(self):
        """
        월별로 각각 카테고리 비율을 계산합니다.
        파이 차트를 달마다 따로 그릴 때 사용해요.

        반환값: {
            'Janvier 2024': {'Transport': {'total': 131, 'pourcentage': 9.6}, ...},
            'Février 2024': {...},
            ...
        }
        """
        resultats_par_mois = {}

        for (annee, mois), groupe in self.depenses.groupby(['Année', 'Mois']):
            cle = f"{MOIS_FR[mois]} {annee}"

            par_categorie = groupe.groupby('Catégorie')['Montant_abs'].sum()
            total_du_mois = par_categorie.sum()

            resultats_par_mois[cle] = {}
            for categorie, montant in par_categorie.items():
                resultats_par_mois[cle][categorie] = {
                    'total': round(montant, 2),
                    'pourcentage': round((montant / total_du_mois) * 100, 1)
                }

        return resultats_par_mois

    def calculer_moyenne_mensuelle(self):
        """
        월별 지출 합계, 전체 평균, 월급이 있으면 잔액도 계산합니다.

        반환값: {
            'moyenne': 1250.50,
            'a_un_salaire': True,
            'par_mois': {
                'Janvier 2024': {
                    'depenses': 1100.0,
                    'salaire':  2500.0,   # 월급 없으면 None
                    'solde':    1400.0    # 월급 - 지출, 없으면 None
                }, ...
            }
        }
        """
        par_mois_depenses = self.depenses.groupby(['Année', 'Mois'])['Montant_abs'].sum()

        # 월급이 있는지 확인
        a_un_salaire = self.revenus['est_salaire'].any() if 'est_salaire' in self.revenus.columns else False

        if a_un_salaire:
            salaires = self.revenus[self.revenus['est_salaire'] == True]
            par_mois_salaires = salaires.groupby(['Année', 'Mois'])['Montant'].sum()

        mois_dict = {}
        for (annee, mois), depense in par_mois_depenses.items():
            cle = f"{MOIS_FR[mois]} {annee}"

            salaire = None
            solde   = None
            if a_un_salaire:
                salaire = par_mois_salaires.get((annee, mois), None)
                if salaire is not None:
                    salaire = round(float(salaire), 2)
                    solde   = round(salaire - depense, 2)

            mois_dict[cle] = {
                'depenses': round(depense, 2),
                'salaire':  salaire,
                'solde':    solde
            }

        moyenne = round(par_mois_depenses.mean(), 2)
        return {
            'moyenne':      moyenne,
            'par_mois':     mois_dict,
            'a_un_salaire': a_un_salaire
        }

    def comparer_budget(self, budgets):
        """
        실제 지출을 설정된 예산과 비교합니다.
        반환값: (resultats 딕셔너리, total_economise 숫자)
        """
        par_categorie = self.depenses.groupby('Catégorie')['Montant_abs'].sum()
        nb_mois = self.depenses.groupby(['Année', 'Mois']).ngroups

        resultats      = {}
        total_economise = 0

        for categorie, budget_mensuel in budgets.items():
            depense_totale = par_categorie.get(categorie, 0)
            budget_total   = budget_mensuel * nb_mois
            ecart          = budget_total - depense_totale

            if ecart >= 0:
                statut = 'économie'
                total_economise += ecart
            else:
                statut = 'dépassement'

            resultats[categorie] = {
                'budget_mensuel': budget_mensuel,
                'budget_total':   round(budget_total, 2),
                'depense_totale': round(depense_totale, 2),
                'ecart':          round(abs(ecart), 2),
                'statut':         statut,
                'nb_mois':        nb_mois
            }

        return resultats, round(total_economise, 2)

    def calculer_epargne(self, budgets, objectif_epargne):
        """
        저축 누적액과 목표 달성률을 계산합니다.
        """
        _, total_economise = self.comparer_budget(budgets)

        restant             = max(0, objectif_epargne - total_economise)
        pourcentage_atteint = min(100, round((total_economise / objectif_epargne) * 100, 1))

        return {
            'epargne_accumulee':   total_economise,
            'objectif':            objectif_epargne,
            'restant':             restant,
            'pourcentage_atteint': pourcentage_atteint
        }

    def analyser_tendances(self):
        """
        카테고리별 + 월별 지출 추세 데이터를 반환합니다.
        반환값: DataFrame (Catégorie, Année, Mois, Montant_abs)
        """
        tendances = self.depenses.groupby(
            ['Catégorie', 'Année', 'Mois']
        )['Montant_abs'].sum().reset_index()

        return tendances