import json
import os
import tempfile
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _salva_grafico(fig, filename: str, out_dir: str = "out_bf_sciopero") -> str:
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, filename)
    try:
        fig.savefig(target, dpi=150, bbox_inches="tight")
        return target
    except OSError:
        fallback = os.path.join(tempfile.gettempdir(), filename)
        fig.savefig(fallback, dpi=150, bbox_inches="tight")
        return fallback
    finally:
        plt.close(fig)


def simula_scenario_bf_sciopero(
    ordini_giorno_base: int = 1200,
    moltiplicatore_bf: float = 2.4,
    quota_arretrato_sciopero: float = 0.35,
    quota_urgenza_arretrato: float = 0.60,
    margine_lordo_ordine_eur: float = 14.0,
    costo_spedizione_urgente_extra_eur: float = 3.5,
    capacita_giornaliera_max_ordini: int = 3100,
    out_dir: str = "out_bf_sciopero",
) -> dict:
    ordini_bf_giorno = ordini_giorno_base * moltiplicatore_bf
    arretrato_sciopero = int(round(ordini_giorno_base * quota_arretrato_sciopero))
    carico_totale_bf = ordini_bf_giorno + arretrato_sciopero

    ordini_urgenza = arretrato_sciopero * quota_urgenza_arretrato
    costo_extra_tot = ordini_urgenza * costo_spedizione_urgente_extra_eur
    margine_lordo_bf = ordini_bf_giorno * margine_lordo_ordine_eur
    margine_netto_con_extra = margine_lordo_bf - costo_extra_tot

    # Verifica capacita operativa rispetto al carico totale del giorno
    eccesso_capacita_ordini = max(0.0, carico_totale_bf - capacita_giornaliera_max_ordini)
    quota_eccesso_su_bf = (
        round(eccesso_capacita_ordini / ordini_bf_giorno * 100.0, 2)
        if ordini_bf_giorno > 0
        else 0.0
    )

    # Tabella di sensibilita su diversi livelli di arretrato e margine unitario
    righe_sensibilita = []
    for arretrato_test in (240, 420, 600, 840):
        for margine_test in (9.0, 11.5, 14.0):
            costo_test = arretrato_test * quota_urgenza_arretrato * costo_spedizione_urgente_extra_eur
            netto_test = margine_lordo_bf - costo_test
            carico_test = ordini_bf_giorno + arretrato_test
            righe_sensibilita.append(
                {
                    "arretrato_ordini": arretrato_test,
                    "margine_lordo_ordine_eur": margine_test,
                    "carico_totale_giorno": int(round(carico_test)),
                    "extra_urgenza_eur": round(costo_test, 2),
                    "margine_netto_giorno_eur": round(netto_test, 2),
                }
            )

    df_sens = pd.DataFrame(righe_sensibilita)

    df_riepilogo = pd.DataFrame(
        [
            {"voce": "ordini_giorno_base", "valore": ordini_giorno_base, "unita": "ordini"},
            {"voce": "ordini_bf_giorno", "valore": int(round(ordini_bf_giorno)), "unita": "ordini"},
            {"voce": "arretrato_sciopero_stimato", "valore": arretrato_sciopero, "unita": "ordini"},
            {"voce": "carico_totale_giorno_bf", "valore": int(round(carico_totale_bf)), "unita": "ordini"},
            {"voce": "capacita_giornaliera_max_ordini", "valore": capacita_giornaliera_max_ordini, "unita": "ordini"},
            {"voce": "eccesso_capacita_ordini", "valore": round(eccesso_capacita_ordini, 1), "unita": "ordini"},
            {"voce": "margine_lordo_bf_giorno", "valore": round(margine_lordo_bf, 2), "unita": "EUR"},
            {"voce": "costo_extra_spedizioni_urgenti", "valore": round(costo_extra_tot, 2), "unita": "EUR"},
            {"voce": "margine_netto_residuo_giorno", "valore": round(margine_netto_con_extra, 2), "unita": "EUR"},
        ]
    )

    os.makedirs(out_dir, exist_ok=True)
    csv_riepilogo = os.path.join(out_dir, "riepilogo_bf_sciopero_milano.csv")
    csv_sens = os.path.join(out_dir, "sensibilita_bf_sciopero_milano.csv")
    json_path = os.path.join(out_dir, "esito_bf_sciopero_milano.json")

    df_riepilogo.to_csv(csv_riepilogo, index=False)
    df_sens.to_csv(csv_sens, index=False)

    riepilogo_dict = {
        "contesto": "Milano - Sciopero logistica/trasporti 20 nov 2026 + picco Black Friday 27 nov 2026",
        "ordini_bf_giorno": int(round(ordini_bf_giorno)),
        "arretrato_sciopero_stimato": arretrato_sciopero,
        "carico_totale_bf": int(round(carico_totale_bf)),
        "capacita_giornaliera_max_ordini": capacita_giornaliera_max_ordini,
        "eccesso_capacita_ordini": round(eccesso_capacita_ordini, 1),
        "quota_eccesso_su_bf_pct": quota_eccesso_su_bf,
        "margine_lordo_bf_eur": round(margine_lordo_bf, 2),
        "costo_extra_tot_eur": round(costo_extra_tot, 2),
        "margine_netto_con_extra_eur": round(margine_netto_con_extra, 2),
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(riepilogo_dict, f, indent=2, ensure_ascii=False)

    # Grafico pulito a due pannelli: carico vs capacita e margine netto vs arretrato
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6))

    ax1, ax2 = axes
    categorie = ["Picco BF", "Arretrato Sciopero", "Carico Totale", "Capacita Max"]
    valori_ordini = [
        ordini_bf_giorno,
        arretrato_sciopero,
        carico_totale_bf,
        capacita_giornaliera_max_ordini,
    ]
    colori_1 = ["#1f4e78", "#c05621", "#2b6cb0", "#4a5568"]
    bars1 = ax1.bar(categorie, valori_ordini, color=colori_1, width=0.55)
    ax1.set_title("Carico Giornaliero vs Capacita Operativa")
    ax1.set_ylabel("Numero ordini")
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    for bar in bars1:
        h = bar.get_height()
        ax1.text(
            bar.get_x() + bar.get_width() / 2.0,
            h + max(valori_ordini) * 0.02,
            f"{h:,.0f}".replace(",", "."),
            ha="center",
            va="bottom",
            fontsize=8.5,
        )

    sub_m14 = df_sens[df_sens["margine_lordo_ordine_eur"] == margine_lordo_ordine_eur]
    ax2.plot(
        sub_m14["arretrato_ordini"],
        sub_m14["margine_netto_giorno_eur"],
        marker="o",
        linewidth=2,
        color="#2e6f40",
        label=f"Margine {margine_lordo_ordine_eur:.0f} EUR/ordine",
    )
    sub_m10 = df_sens[df_sens["margine_lordo_ordine_eur"] == 11.5]
    ax2.plot(
        sub_m10["arretrato_ordini"],
        sub_m10["margine_netto_giorno_eur"],
        marker="s",
        linewidth=2,
        linestyle="--",
        color="#b7791f",
        label="Margine 11,5 EUR/ordine",
    )
    ax2.set_title("Margine Netto Giornaliero al Variare dell'Arretrato")
    ax2.set_xlabel("Ordini arretrati da smaltire")
    ax2.set_ylabel("Margine netto residuo (EUR)")
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2.legend(fontsize=8.5)

    fig.tight_layout()
    grafico_path = _salva_grafico(fig, "carico_e_margine_bf_sciopero.png", out_dir=out_dir)

    print("=== SIMULAZIONE FINE NOVEMBRE 2026 (MILANO) ===")
    print(
        f"Ordini BF/giorno: {ordini_bf_giorno:.0f} | Arretrato stimato: {arretrato_sciopero} | "
        f"Carico totale giorno BF: {carico_totale_bf:.0f}"
    )
    print(
        f"Capacita max: {capacita_giornaliera_max_ordini} | Eccesso carico: {eccesso_capacita_ordini:.0f} ordini"
    )
    print(
        f"Margine lordo BF (1 giorno): {margine_lordo_bf:,.0f} EUR | Extra costi urgenza: {costo_extra_tot:,.0f} EUR | "
        f"Residuo: {margine_netto_con_extra:,.0f} EUR".replace(",", ".")
    )
    print(f"File salvati in '{out_dir}/': {csv_riepilogo}, {csv_sens}, {json_path}, {grafico_path}")

    return riepilogo_dict


if __name__ == "__main__":
    simula_scenario_bf_sciopero()