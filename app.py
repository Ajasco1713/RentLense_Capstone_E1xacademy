import pandas as pd
import streamlit as st

from services.demo_data import demo_properties
from services.parser import parse_requirements
from services.ranking import rank_properties
from services.rentcast import RentCastError, search_rentals

st.set_page_config(page_title="RentLense", page_icon="🏠", layout="wide")

st.title("🏠 RentLense")
st.caption("An Intelligent System for Finding the Right Rental Property")

DEFAULT_QUERY = (
    "I need a 2-bedroom apartment in Austin, Texas below $3000 per month "
    "with parking and security."
)

with st.sidebar:
    st.header("Search preferences")
    query = st.text_area("Describe your ideal rental", DEFAULT_QUERY, height=130)
    use_demo = st.toggle("Use demo data", value=True)
    top_k = st.slider("Number of results", min_value=1, max_value=20, value=8)
    st.divider()
    st.caption("Demo mode uses a small built-in dataset and needs no API key.")


def money(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"${float(value):,.0f}/month"


def show_property(row):
    address = row.get("formattedAddress", "Property")
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.subheader(address)
            st.write(
                f"**{row.get('propertyType', 'Unknown')}** · "
                f"{row.get('bedrooms', 'N/A')} bed · "
                f"{row.get('bathrooms', 'N/A')} bath · "
                f"{money(row.get('price'))}"
            )
        with c2:
            st.metric("Match", f"{float(row.get('match_score', 0)):.0f}%")

        details = []
        if pd.notna(row.get("squareFootage")):
            details.append(f"Size: {float(row['squareFootage']):,.0f} sq ft")
        if pd.notna(row.get("yearBuilt")):
            details.append(f"Built: {int(row['yearBuilt'])}")
        if row.get("status"):
            details.append(f"Status: {row['status']}")
        if details:
            st.caption(" · ".join(details))

            
        # Additional cost transparency
        with st.expander("💰 Additional costs and estimated total", expanded=True):
            def find_cost(*field_names):
                for field in field_names:
                    value = row.get(field)
                    if value is not None and pd.notna(value):
                        try:
                            return float(value)
                        except (TypeError, ValueError):
                            continue
                return None

            rent = find_cost("price")
            deposit = find_cost("securityDeposit", "security_deposit")
            application_fee = find_cost("applicationFee", "application_fee")
            parking_fee = find_cost("parkingFee", "parking_fee", "parkingCost")
            pet_fee = find_cost("petFee", "pet_fee")

            st.write("**Advertised monthly rent:**",
                     f"${rent:,.2f}" if rent is not None else "Not provided")

            st.write("**Security deposit:**",
                     f"${deposit:,.2f}" if deposit is not None else "Not provided")

            st.write("**Application fee:**",
                     f"${application_fee:,.2f}" if application_fee is not None else "Not provided")

            st.write("**Parking fee:**",
                     f"${parking_fee:,.2f}/month" if parking_fee is not None else "Not provided")

            st.write("**Pet fee:**",
                     f"${pet_fee:,.2f}" if pet_fee is not None else "Not provided")

            if rent is not None and parking_fee is not None:
                st.metric(
                    "Rent + known monthly parking fee",
                    f"${rent + parking_fee:,.2f}/month"
                )
            elif rent is not None:
                st.metric("Advertised rent", f"${rent:,.2f}/month")
                st.caption(
                    "Other monthly costs are not included because their amounts "
                    "have not been confirmed."
                )

            if rent is not None and deposit is not None and application_fee is not None:
                st.metric(
                    "Known initial cost (rent + deposit + application fee)",
                    f"${rent + deposit + application_fee:,.2f}"
                )

            st.caption(
                "Missing fees are marked 'Not provided'. These figures are "
                "estimates based only on available listing data; other charges may apply."
            )

        if row.get("description"):
            st.write(row["description"])

        reasons = row.get("match_reasons", [])
        if isinstance(reasons, list) and reasons:
            st.success("Why it matches: " + " • ".join(reasons))

        with st.expander("Match breakdown"):
            breakdown = row.get("score_breakdown", {})
            if breakdown:
                st.dataframe(
                    pd.DataFrame(
                        [{"Requirement": k, "Points": round(v, 1)} for k, v in breakdown.items()]
                    ),
                    hide_index=True,
                    use_container_width=True,
                )


if st.button("🔎 Find matching properties", type="primary", use_container_width=True):
    if not query.strip():
        st.warning("Please describe the rental property you want.")
        st.stop()

    requirements = parse_requirements(query)

    with st.expander("🧠 Structured requirements", expanded=True):
        st.json(requirements)

    try:
        if use_demo:
            raw_df = demo_properties()
        else:
            raw_df = search_rentals(requirements)

        ranked = rank_properties(raw_df, requirements).head(top_k).copy()

        if ranked.empty:
            st.warning("No matching properties found. Try relaxing one requirement.")
            st.stop()

        st.success(f"Found {len(ranked)} matching properties.")

        # Summary metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Results", len(ranked))
        m2.metric("Best match", f"{ranked['match_score'].max():.0f}%")
        m3.metric("Avg. rent", money(ranked["price"].mean()) if "price" in ranked else "N/A")
        m4.metric("Source", "Demo" if use_demo else "RentCast")

        for _, row in ranked.iterrows():
            show_property(row)

        st.download_button(
            "⬇️ Download CSV",
            ranked.to_csv(index=False),
            file_name="rentlense_results.csv",
            mime="text/csv",
            use_container_width=True,
        )

    except RentCastError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Unexpected application error: {exc}")
