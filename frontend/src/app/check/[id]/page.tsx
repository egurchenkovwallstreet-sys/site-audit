import { CheckView } from "./CheckView";

type Props = { params: Promise<{ id: string }> };

export default async function CheckPage({ params }: Props) {
  const { id } = await params;
  return <CheckView scanId={id} />;
}