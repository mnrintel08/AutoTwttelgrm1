from DuplTwi_R0_0_var import *
import requests
import urllib.parse
import m3u8
import sys
import asyncio
import aiohttp
import os


def solicitarToken(vodID):
    global url_api
    global cabecera_token

    bdy_token = [
        {
            'operationName':'PlaybackAccessToken_Template',
            'query': 'query PlaybackAccessToken_Template($login: String!, $isLive: Boolean!, $vodID: ID!, $isVod: '
                     'Boolean!, $playerType: String!) {  streamPlaybackAccessToken(channelName: $login, params: '
                     '{platform: \"web\", playerBackend: \"mediaplayer\", playerType: $playerType}) '
                     '@include(if: $isLive) {    value    signature    __typename  }  videoPlaybackAccessToken'
                     '(id: $vodID, params: {platform: \"web\", playerBackend: \"mediaplayer\", playerType: '
                     '$playerType}) @include(if: $isVod) {    value    signature    __typename  }}',
            'variables':{
                'isLive':False,
                'login':'',
                'isVod': True,
                'vodID': vodID,
                'playerType': 'site'
            }
        }
    ]

    respuesta_token = requests.post(url_api, json=bdy_token, headers=cabecera_token)
    contenido_token = respuesta_token.json()

    firma = contenido_token[0]['data']['videoPlaybackAccessToken']['signature']
    token = contenido_token[0]['data']['videoPlaybackAccessToken']['value']
    token_cod = urllib.parse.quote(token, safe='')

    return firma, token_cod


def obtenerReso(vodID, firma, token_cod):
    global cabecera_m3u8
    
    url_reso = 'https://usher.ttvnw.net/vod/' + vodID + '.m3u8?allow_source=true& player_backend=mediaplayer&' \
               'playlist_include_framerate=true&reassignments_supported=true&sig=' + firma + '&supported_codecs=' \
               'avc1&token=' + token_cod + '&cdm=wv&player_version=1.5.0'

    arch_reso = requests.get(url_reso, headers=cabecera_m3u8)

    m3u8_reso = m3u8.loads(arch_reso.text)

    return m3u8_reso.data['playlists'][0]['uri']


def obtenerJSON(vodID):
    global url_api
    global cabecera_data
    
    bdy_data = [
        {
            'operationName':'ComscoreStreamingQuery',
            'variables':{
                'channel':'',
                'clipSlug':'',
                'isClip': False,
		'isLive': False,
		'isVodOrCollection':  True,
                'vodID': vodID,
            },
	    'extensions': {
		    'persistedQuery': {
			    'version': 1,
			    'sha256Hash': 'e1edae8122517d013405f237ffcc124515dc6ded82480a88daef69c83b53ac01'
			}
		}
        }
    ]

    respuesta_data = requests.post(url_api, json=bdy_data, headers=cabecera_data)
    data = respuesta_data.json()

    return data[0]['data']['video']


def obtenerFrag(url_frag):
    global cabecera_m3u8

    arch_frag = requests.get(url_frag, headers=cabecera_m3u8)

    m3u8_frag = m3u8.loads(arch_frag.text)

    return m3u8_frag.data['segments']


def obtenerFecha(fecha):
    fech_vid = fecha.split('T')[0]
    
    dia = fech_vid.split('-')[2]
    mes = fech_vid.split('-')[1]
    anio = fech_vid.split('-')[0]
    
    fech_vid = dia + "-" + mes + '-' + anio

    return fech_vid


async def descargarFrag(session, url, i):
    async with session.get(url, timeout=1000) as respuesta:
        if respuesta.status == 200:
            contenido = await respuesta.content.read()
            with open("./ts/" + str(i) + ".ts", "wb") as fragmento:
                fragmento.write(contenido)
        else:
            os.system("echo URL: " + url)
            os.system("echo status: " + str(respuesta.status))


async def realizarTareas(url_ts, lista_frag):
    async with aiohttp.ClientSession() as session:
        tareas = [descargarFrag(session, url_ts + item['uri'], i) for i, item in enumerate(lista_frag)]
        await asyncio.gather(*tareas)


if __name__ == '__main__':
    
    LINKS_CHNL = sys.argv[1].split(",")
    VOIDS = sys.argv[2].split(",")

    
    for v, vodID in enumerate(VOIDS):
        datos_vid = obtenerJSON(vodID)
        titulo_vid = datos_vid['title']
        fecha_vid = obtenerFecha(datos_vid['createdAt'])
        streamer = datos_vid['owner']['displayName']
        nom_modf = titulo_vid

        for simbolo in lst_nomSim:
            nom_modf = nom_modf.replace(simbolo, lst_nomSim[simbolo])

        os.system("echo Nombre Original: " + titulo_vid)
        os.system("echo Nombre Modificado:  " + nom_modf)

        firma, token = solicitarToken(vodID)
        url_frag = obtenerReso(vodID, firma, token)
        lista_frag = obtenerFrag(url_frag)
        url_ts = url_frag[:len(url_frag)- url_frag[::-1].index('/')]
        
        os.system("echo -------------------------------------------------")
        os.system("echo URL HLS Fragmentos: " + url_frag)
        os.system("echo URL HLS Base TS: " + url_ts)

        if len(nom_modf + "_XX.ts") > 58:
            nom_vid = nom_modf[:58] + " [...]"
        else:
            nom_vid = nom_modf
        
        os.system("echo -------------------------------------------------")
        os.system("echo Nombre de archivo recortado: \n")
        os.system("echo " + nom_vid)

        os.system("echo -------------------------------------------------")
        os.system("echo Descarga de Fragmentos. Errores:")
        os.system("mkdir ts")
        asyncio.run(realizarTareas(url_ts, lista_frag))

        os.system("echo -------------------------------------------------")
        os.system("echo Union de archivos TS")
        os.system("mkdir " + streamer + "_" + fecha_vid)
        dir_vid = streamer + "_" + fecha_vid
        cont_frag = 0
        for i in range(len(lista_frag)):
            with open("./" + dir_vid + "/" + nom_vid + "_" + str(cont_frag) + ".ts", "ab") as arch_ts:
                peso_arch = os.stat("./" + dir_vid + "/" + nom_vid + "_" + str(cont_frag) + ".ts").st_size
                peso_arch = peso_arch/1024/1024/1024
                with open("./ts/" + str(i) + ".ts", "rb") as fragmento:
                    peso_frag = os.stat("./ts/" + str(i) + ".ts").st_size
                    peso_frag = peso_frag/1024/1024/1024
                    if peso_arch + peso_frag > 1.8:
                        cont_frag += 1
                    arch_ts.write(fragmento.read())
                os.remove("./ts/" + str(i) + ".ts")
        os.rmdir("ts")

        os.system("echo -------------------------------------------------")
        os.system("echo Subir Fragmentos")

        lst_arch = '"' + dir_vid + '/' + '" "{dirc}/'.format(dirc=dir_vid).join(os.listdir(dir_vid)) + '"'
        os.system("echo telegram-upload --to {link} --force-file --caption {fecha} {archivos}".format(link=LINKS_CHNL[v], fecha=fecha_vid, archivos=lst_arch))
        os.system("telegram-upload --to {link} --force-file --caption {fecha} {archivos}".format(link=LINKS_CHNL[v], fecha=fecha_vid, archivos=lst_arch))

        os.system("echo -------------------------------------------------")

        os.system("RD /S /Q {directorio}".format(directorio=dir_vid))

        

        

    

    
