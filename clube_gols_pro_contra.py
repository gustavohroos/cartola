from sys import argv
import pandas as pd
from pymongo import DESCENDING, MongoClient
from escalador import Recommender

def main(argv):
    min_rodadas = 4

    client = MongoClient('localhost', 27017)
    db = client['cartola']
    atletas_collection = db.atletas_rodada
    partidas = list(db.partidas_rodada.find())
    clubes = normalizar_clubes(db.clube.find(), partidas)

    goleiros = carregar_atletas_probab_menos_gols(1, min_rodadas, clubes, atletas_collection).set_index('atleta_id')
    laterais = carregar_atletas_probab_menos_gols(2, min_rodadas, clubes, atletas_collection).set_index('atleta_id')
    zagueiros = carregar_atletas_probab_menos_gols(3, min_rodadas, clubes, atletas_collection).set_index('atleta_id')
    meias = carregar_atletas_meias(4, min_rodadas, clubes, atletas_collection).set_index('atleta_id')
    atacantes = carregar_atletas_probab_mais_gols(5, min_rodadas, clubes, atletas_collection).set_index('atleta_id')
    tecnicos = carregar_atletas_probab_mais_gols(6, min_rodadas, clubes, atletas_collection).set_index('atleta_id')

    recommender = Recommender(float(argv[1]), argv[2], argv[3], argv[4], argv[5])
    recommender.melhor_time_possivel(goleiros, laterais, zagueiros, meias, atacantes, tecnicos)
    recommender.escalar_limitando_preco(goleiros, laterais, zagueiros, meias, atacantes, tecnicos)
    recommender.imprimir_escalacao(atletas_collection)

    client.close()

def normalizar_clubes(clubes, partidas):
    clubes = pd.DataFrame(list(clubes)).set_index('_id')
    #clubes['gols_pro_mandante_norm'] = normalizar_df_min_max(clubes['gols_pro_mandante'])
    #clubes['gols_pro_visitante_norm'] = normalizar_df_min_max(clubes['gols_pro_visitante'])

    #gols sofrido têm peso invertido
    #clubes['gols_sofridos_mandante_norm'] = -1*normalizar_df_min_max(clubes['gols_sofridos_mandante'])
    #clubes['gols_sofridos_visitante_norm'] = -1*normalizar_df_min_max(clubes['gols_sofridos_visitante'])

    for partida in partidas:
        clubes.loc[partida['clube_casa_id'], 'saldo_pro'] = clubes.loc[partida['clube_casa_id'],'gols_pro_mandante']\
                + clubes.loc[partida['clube_visitante_id'],'gols_sofridos_visitante']
        clubes.loc[partida['clube_casa_id'], 'saldo_sofridos'] = clubes.loc[partida['clube_casa_id'],'gols_sofridos_mandante']\
                + clubes.loc[partida['clube_visitante_id'],'gols_pro_visitante']
        clubes.loc[partida['clube_visitante_id'], 'saldo_pro'] = clubes.loc[partida['clube_visitante_id'],'gols_pro_visitante']\
                + clubes.loc[partida['clube_casa_id'],'gols_sofridos_mandante']
        clubes.loc[partida['clube_visitante_id'], 'saldo_sofridos'] = clubes.loc[partida['clube_visitante_id'],'gols_sofridos_mandante']\
                + clubes.loc[partida['clube_casa_id'],'gols_pro_visitante']

    clubes['saldo_pro_normalizado'] = normalizar_df_min_max(clubes['saldo_pro'])
    # gols sofrido têm peso invertido
    clubes['saldo_sofridos_normalizado'] = -1*normalizar_df_min_max(clubes['saldo_sofridos'])
    return clubes

def carregar_atletas_probab_menos_gols(posicao, min_rodadas, clubes, atletas_collection):
    return carregar_atletas_probab_gols('sofridos', posicao, min_rodadas, clubes, atletas_collection).sort_values('power',ascending=False)

def carregar_atletas_probab_mais_gols(posicao, min_rodadas, clubes, atletas_collection):
    return carregar_atletas_probab_gols('pro', posicao, min_rodadas, clubes, atletas_collection).sort_values('power',ascending=False)

def carregar_atletas_probab_gols(index, posicao, min_rodadas, clubes, atletas_collection):
    atletas = carregar_atletas(posicao, min_rodadas, atletas_collection)
    atletas = pd.merge(atletas, clubes, how='left', left_on='clube_id', right_index=True)
    atletas['power'] = atletas['saldo_'+index+'_normalizado'] + atletas['media_normalizada']
    return atletas

def carregar_atletas_meias(posicao, min_rodadas, clubes, atletas_collection):
    atletas_defesa = carregar_atletas_probab_menos_gols(posicao, min_rodadas, clubes, atletas_collection)
    atletas_ataque = carregar_atletas_probab_mais_gols(posicao, min_rodadas, clubes, atletas_collection)
    atletas_ataque['power'] = (atletas_defesa['power'] + atletas_ataque['power']) / 2
    return atletas_ataque.sort_values('power',ascending=False)

def carregar_atletas(posicao, min_rodadas, atletas_collection):
    atletas_df = pd.DataFrame(list(atletas_collection.find({"jogos_num": {"$gte": min_rodadas}, "posicao_id": posicao}).sort([("media_num", DESCENDING)])))
    atletas_df['media_normalizada'] = normalizar_df_min_max(atletas_df['media_num'])
    return atletas_df

def normalizar_df_min_max(dataframe):
    return (dataframe - dataframe.mean()) / (dataframe.max() - dataframe.min())

if __name__ == "__main__":
    main(argv)